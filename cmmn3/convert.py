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

def convertCtx(evtPath, dynPath, modelNs, destPath=None):

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

    def convert_dyn_ctx(case_uri, dyn_ctx, modelNs):
        g = Graph()

        for _, row in dyn_ctx.iterrows():
            concept = concept_map[row['concept:name']]
            value = row['value']
            fhir_obs(g, case_uri, concept, value)

        return QuotedGraph(g.store, g.identifier)

    def convert_stat_ctx(case_uri, stat_ctx, modelNs):
        g = Graph()

        if stat_ctx['discharge_disposition'].startswith("Admit to reporting facility as inpatient"):
            concept = concept_map['admitted']
            fhir_obs(g, case_uri, concept)

        diagn_codes = parse_list(stat_ctx['all_diagnoses'])
        for diagn_code in diagn_codes:
            if not icd.is_valid_item(diagn_code):
                print("cannot find ICD-10 item:", diagn_code)
                descr = "unknown"
            else:
                descr = icd.get_description(diagn_code)
            concept = [ icd10_sys, ICD[diagn_code], descr ]
            fhir_cond(g, case_uri, concept)

        age = int(stat_ctx['age'])
        g.add(( case_uri, FHR['birthDate'], Literal(age) ))

        return QuotedGraph(g.store, g.identifier)

    # lookup dynamic ctx based on timestamp
    ddf = pd.read_csv(dynPath, index_col=0)
    ddf['time:timestamp'] = pd.to_datetime(ddf['time:timestamp'])
    ddf['time:until'] = ddf.groupby([ 'case:concept:name', 'concept:name' ])['time:timestamp'].shift(-1)
    dtimes = ddf.rename({"time:timestamp": "time:from"}, axis=1)
    # dtimes[dtimes['case:concept:name']==88]

    edf = pd.read_csv(evtPath, index_col=0)

    statg = Graph(); dyng = Graph()
    total_cases = len(edf['case:concept:name'].unique())
    for cnt, (case, group) in enumerate(edf.groupby('case:concept:name')):
        if cnt % 500 == 0:
            print(f"case #{cnt} / {total_cases}")

        case_uri = str_to_uri(f"case_{case}", modelNs)

        ctxs = []; idx_ctx = {}; 
        align = [] # aligns each event with ctx ID

        # get static ctx (incl. diagnoses)
        stat_ctx = group.iloc[0]
        stat_ctx_qg = convert_stat_ctx(case_uri, stat_ctx, modelNs)
        statg.add(( case_uri, CM['stat_ctx'], stat_ctx_qg ))

        # print(case)
        for index, row in group.iterrows():
            # print(index, row['case:concept:name'], row['time:timestamp'])

            # get dynamic ctx
            dyn_ctx = dtimes[
                (dtimes['case:concept:name'] == row['case:concept:name']) & 
                (row['time:timestamp'] >= dtimes['time:from']) & ( (row['time:timestamp'] <= dtimes['time:until']) | ( dtimes['time:until'].isna() ) )
            ]

            # ctx identifier = row indexes
            idx = tuple(dyn_ctx.index)
            # ctx already encountered; re-use ID
            if idx in idx_ctx:
                ctx_nr = idx_ctx[idx]
            else:
                # add new ctx & get ID
                ctx_nr = len(ctxs)
                ctxs.append(convert_dyn_ctx(case_uri, dyn_ctx, modelNs))
                idx_ctx[idx] = ctx_nr
            
            # add ctx ID for event
            align.append(Literal(ctx_nr))

        # afterwards, add event alignment & ctxs to graph
        dyng.add(( case_uri, CM['alignment'], rdf_coll(dyng, *align) ))
        dyng.add(( case_uri, CM['dyn_ctxs'], rdf_coll(dyng, *ctxs) ))

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
        
        curCtx = itemObj['ctxs'][-1]
        g.add((planItemUri, ST['in'], rdf_coll(g, ST[curCtx[0]], Literal(curCtx[1]))))
                
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