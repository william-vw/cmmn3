import os, csv
import pandas as pd
from rdflib import Literal, Graph, BNode, RDF, RDFS, XSD, URIRef
from rdflib.collection import Collection
from rdflib.graph import QuotedGraph
from cmmn3.ns import CM, ST, RE, SCT, FHR, ICD
from util import rdf_coll, print_rdf_stmt, str_to_uri, parse_list
import simple_icd_10 as icd

sct_sys = URIRef("http://www.snomed.org")
icd10_sys = URIRef("http://hl7.org/fhir/sid/icd-10")

concept_map = {
    "BP systolic": ( sct_sys, SCT['271649006'], "Systolic blood pressure" ),
    "BP diastolic": ( sct_sys, SCT['271650006'], "Diastolic blood pressure" ),
    "Heart rate": ( sct_sys, SCT['364075005'], "Heart rate" ),
    "Body Temperature ": ( sct_sys, SCT['386725007'], "Body temperature" ),
    "Respiratory rate": ( sct_sys, SCT['364062005'], "Respiration observable" ),
    "admitted": ( sct_sys, SCT['308540004'], "Inpatient stay" )
}

def convertState(evtPath, dynPath, staticPath, modelNs, destPath=None):

    def fhir_thing(g, subj, coding, type, value=None):
        thing = BNode()
        # vastly simplified for now
        # e.g., https://build.fhir.org/observation-example-f001-glucose.ttl.html
        g.add(( subj, FHR["subjectOf"], thing ))
        # g.add(( thing, FHR["subject"], subj ))
        g.add(( thing, RDF['type'], type ))
        g.add(( thing, FHR["code"], coding[1] ))
        g.add(( thing, RDFS["label"], Literal(coding[2]) ))
        if value is not None:
            g.add(( thing, FHR["value"], Literal(value, datatype=XSD['decimal']) ))

    def fhir_cond(g, subj, coding):
        fhir_thing(g, subj, coding, FHR['Condition'])

    def fhir_obs(g, subj, coding, value=None):
        fhir_thing(g, subj, coding, FHR['Observation'], value)

    def convert_dyn_state(case_uri, stat_state, diagn_state, dyn_state, modelNs):
        g = Graph()

        for _, row in stat_state.iterrows():
            concept = concept_map[row['state']]
            fhir_obs(g, case_uri, concept)

        for diagn_code in diagn_state:
            # throws error if not found
            descr = icd.get_description(diagn_code)
            concept = [ icd10_sys, ICD[diagn_code], descr ]
            fhir_cond(g, case_uri, concept)

        for _, row in dyn_state.iterrows():
            concept = concept_map[row['concept:name']]
            value = row['value']
            fhir_obs(g, case_uri, concept, value)

        return QuotedGraph(g.store, g.identifier)

    def convert_stat_state(case_uri, stat_state, diagn_state, modelNs):
        g = Graph()

        for _, row in stat_state.iterrows():
            concept = concept_map[row['state']]
            fhir_obs(g, case_uri, concept)

        for diagn_code in diagn_state:
            # throws error if not found
            descr = icd.get_description(diagn_code)
            concept = [ icd10_sys, ICD[diagn_code], descr ]
            fhir_cond(g, case_uri, concept)

        return QuotedGraph(g.store, g.identifier)

    # lookup dynamic state based on timestamp
    ddf = pd.read_csv(dynPath, index_col=0)
    ddf['time:timestamp'] = pd.to_datetime(ddf['time:timestamp'])
    ddf['time:until'] = ddf.groupby([ 'case:concept:name', 'concept:name' ])['time:timestamp'].shift(-1)
    dtimes = ddf.rename({"time:timestamp": "time:from"}, axis=1)
    # dtimes[dtimes['case:concept:name']==88]

    sdf = pd.read_csv(staticPath, index_col=0)
    edf = pd.read_csv(evtPath, index_col=0)

    statg = Graph(); dyng = Graph()
    total_cases = len(edf['case:concept:name'].unique())
    for cnt, (case, group) in enumerate(edf.groupby('case:concept:name')):
        if cnt % 100 == 0:
            print(f"case #{cnt} / {total_cases}")

        case_uri = str_to_uri(f"case_{case}", modelNs)

        states = []; idx_state = {}; 
        align = [] # aligns each event with state ID

        # get static state (incl. diagnoses)
        stat_state = sdf[sdf['case:concept:name']==case]
        diagn_state = parse_list(group.iloc[0]['all_diagnoses'])
        stat_state_qg = convert_stat_state(case_uri, stat_state, diagn_state, modelNs)
        statg.add(( case_uri, CM['statstate'], stat_state_qg ))

        # print(case)
        for index, row in group.iterrows():
            # print(index, row['case:concept:name'], row['time:timestamp'])

            # get dynamic state
            dyn_state = dtimes[
                (dtimes['case:concept:name'] == row['case:concept:name']) & 
                (row['time:timestamp'] >= dtimes['time:from']) & ( (row['time:timestamp'] <= dtimes['time:until']) | ( dtimes['time:until'].isna() ) )
            ]

            # state identifier = row indexes
            idx = tuple(dyn_state.index)
            # state already encountered; re-use ID
            if idx in idx_state:
                state_nr = idx_state[idx]
            else:
                # add new state & get ID
                state_nr = len(states)
                states.append(convert_dyn_state(case_uri, stat_state, diagn_state, dyn_state, modelNs))
                idx_state[idx] = state_nr
            
            # add state ID for event
            align.append(Literal(state_nr))

        # afterwards, add event alignment & states to graph
        dyng.add(( case_uri, CM['alignment'], rdf_coll(dyng, *align) ))
        dyng.add(( case_uri, CM['dynstates'], rdf_coll(dyng, *states) ))

        if case == 88:
            break
    
    if destPath is not None:
        statg.serialize(format="n3", destination=os.path.join(destPath, "static.n3"))
        dyng.serialize(format="n3", destination=os.path.join(destPath, "dynamic.n3"))
    else:
        return statg, dyng

def convertLog(path, modelNs, destPath=None, singleFile=True):
    
    def to_stmts(rdf_evts, case, modelNs):
        case_uri = str_to_uri(f"case_{case}", modelNs)
        return ( print_rdf_stmt(case_uri, CM['trace'], rdf_evts), )
        # return ( print_rdf_stmt(case_uri, CM['trace'], rdf_evts), print_rdf_stmt(case_uri, CM['case'], Literal(case)) )
    
    case_stmts = []
    with open(path, newline='') as fh:
        reader = csv.DictReader(fh, delimiter=',')
        next(reader) # skip header
        
        cur = None; rdf_evts = []
        for row in reader:
            case = row['case:concept:name']; evt = row['concept:name']; ts = row['time:timestamp']
            if cur is None:
                cur = case
            elif cur != case:
                case_stmts.append( ( cur, to_stmts(rdf_evts, cur, modelNs) ) )
                cur = case; rdf_evts = []
            
            planItemUri = str_to_uri(evt, modelNs)
            rdf_evts.append( ( planItemUri, ST['Completed'], RE['observation'] ) )
    
    if cur is not None:
        case_stmts.append( ( cur, to_stmts(rdf_evts, case, modelNs) ) )
    
    if destPath:
        if singleFile:
            with open(destPath, 'w') as fh:
                for case, stmts in case_stmts:
                    fh.write("\n".join(stmts) + "\n")
        else:
            for case, stmts in case_stmts:
                obsPath = os.path.join(destPath, f"obs{case}.ttl")
                with open(obsPath, 'w') as fh:
                    fh.write("\n".join(stmts))
    else:
        return case_stmts
        

def convertModel(itemObjs, modelNs, dest):
    g = Graph()

    for label, itemObj in itemObjs.items():
        planItemUri = str_to_uri(label, modelNs)

        if itemObj['label'].strip() != "":
            g.add((planItemUri, RDFS['label'], Literal(itemObj['label'])))
        
        g.add((planItemUri, CM['isMandatory'], Literal(itemObj['mandatory'], datatype=XSD['boolean'])))
        g.add((planItemUri, CM['hasRepetition'], Literal(itemObj['repetition'], datatype=XSD['boolean'])))

        g.add((planItemUri, RDF['type'], CM['PlanItem']))    
        g.add((planItemUri, RDF['type'], CM[itemObj['type']]))
        if itemObj['type'] == 'Stage':
            for child in itemObj['children']:
                g.add((planItemUri, CM['hasChild'], str_to_uri(child, modelNs)))
        
        curState = itemObj['states'][-1]
        g.add((planItemUri, ST['in'], rdf_coll(g, ST[curState[0]], Literal(curState[1]))))
                
        for sentry in itemObj['sentries']['entry']:
            sentryUri = str_to_uri(sentry['id'], modelNs)
            g.add((planItemUri, CM['hasSentry'], sentryUri))
            g.add((sentryUri, RDF['type'], CM['Sentry']))
            g.add((sentryUri, RDF['type'], CM['EntrySentry']))
            
            for item in sentry['items']:
                planItemPartUri = str_to_uri(item['id'], modelNs)
                g.add((sentryUri, CM['hasPlanItemPart'], planItemPartUri))
                
                sourceUri = str_to_uri(item['source'], modelNs)
                g.add((planItemPartUri, CM['hasSource'], sourceUri))
                
                eventLabel = item['event']
                g.add((planItemPartUri, CM['hasEvent'], Literal(eventLabel)))
                
            for condition in sentry['conditions']:
                conditionUri = str_to_uri(condition['id'], modelNs)
                g.add((sentryUri, CM['hasCondition'], conditionUri))
                
                g.add((conditionUri, RDFS['comment'], Literal(condition['text'])))
                
    g.serialize(format="n3", destination=dest)