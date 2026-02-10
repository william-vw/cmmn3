import os, csv
from rdflib import Literal, Graph, BNode, RDF, RDFS, XSD, URIRef
from rdflib.collection import Collection
from cmmn3.ns import CM, ST, RE
from util import rdf_coll, print_rdf_stmt
from util import str_to_uri

def convertLog(path, modelNs, destPath=None, singleFile=True):
    
    def to_trace_stmt(rdf_evts, case):
        # return print_rdf_stmt(rdf_evts, RDF['type'], CM['Trace'])
        return print_rdf_stmt(rdf_evts, CM['trace'], Literal(case))
    
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
                case_stmts.append( ( cur, to_trace_stmt(rdf_evts, case) ) )
                cur = case; rdf_evts = []
            
            planItemUri = str_to_uri(evt, modelNs)
            rdf_evts.append( ( planItemUri, ST['Completed'], RE['observation'] ) )
    
    if cur is not None:
        case_stmts.append( ( cur, to_trace_stmt(rdf_evts, case) ) )
    
    if destPath:
        if singleFile:
            with open(destPath, 'w') as fh:
                for case, stmt in case_stmts:
                    fh.write(stmt + "\n")
        else:
            for case, stmt in case_stmts:
                obsPath = os.path.join(destPath, f"obs{case}.ttl")
                with open(obsPath, 'w') as fh:
                    fh.write(stmt)
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