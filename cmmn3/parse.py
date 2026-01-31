from rdflib import Literal, Graph, BNode, RDF, RDFS, XSD, URIRef
from rdflib.collection import Collection
from rdflib.namespace import split_uri
from cmmn3.ns import ST

from util import uri_to_str

def parseOut(out, itemObjs):
    g = Graph()
    g.parse(data=out)
    
    errors = {}; finals = {}

    for item, _, o in g.triples( ( None, ST['all'], None ) ):
        item = uri_to_str(split_uri(item)[1])
        itemId = itemObjs[item]['id']

        states = [ state for state in Collection(g, o) ]
        for idx, state in enumerate(states):
            typ, dnode = Collection(g, state)
            _, typ = split_uri(typ)
            
            if idx == len(states) - 1:
                finals[item] = { 'item': itemId, 'state': typ }
            
            desc = Collection(g, dnode)
            if len(desc) > 1:
                _, error = desc
                _, error = split_uri(error)
                errors[item] = { 'item': itemId, 'error': error, 'state': typ }

    return errors, finals


import xml.etree.ElementTree as ET

def parseModel(path, ns):
    tree = ET.parse(path)
    for prefix, uri in ns.items():
        ET.register_namespace(prefix, uri)
    root = tree.getroot()
    
    labelToObj = {}
    refToObj = {}
    stages =[]
    stageCnt = 0
    
    planItems = root.findall(".//cmmn:planItem", namespaces=ns)
    for planItem in planItems:
        defRef = planItem.attrib['definitionRef']
        
        itemObj = {
            'id': planItem.attrib['id'],
            'ref': defRef,
            'sentries': {
                'entry': [],
                'exit': []
            }
        }
        
        reqRules = planItem.findall(".//cmmn:itemControl/cmmn:requiredRule", namespaces=ns)
        repRules = planItem.findall(".//cmmn:itemControl/cmmn:repetitionRule", namespaces=ns)
        mandatory = len(reqRules) > 0; repetition = len(repRules) > 0
        itemObj['mandatory'] = mandatory
        itemObj['repetition'] = repetition
        
        label = None; typ = None
        if defRef.startswith("Task"):
            typ = 'Task'
            labelNode = root.findall(f".//cmmn:task[@id='{defRef}']", namespaces=ns)[0]
            label = labelNode.attrib['name']
        elif defRef.startswith("Stage"):
            typ = 'Stage'
            stage = root.findall(f".//cmmn:stage[@id='{defRef}']", namespaces=ns)[0]
            label = stage.attrib['name']
            if label == "":
                stageCnt += 1; label = f'Stage{stageCnt}'
            stages.append((stage, itemObj))
        elif defRef.startswith("Milestone"):
            typ = 'Milestone'
            milestone = root.findall(f".//cmmn:milestone[@id='{defRef}']", namespaces=ns)[0]
            label = milestone.attrib['name']
        else:
            continue
            
        labelToObj[label] = itemObj
        refToObj[defRef] = itemObj
            
        itemObj['label'] = label
        itemObj['type'] = typ
        itemObj['states'] = [ ( 'Inactive', 'init' ) ]
            
        # print(">", label, ("(mandatory)" if mandatory else ""))
        
        for entryCrit in planItem.findall("cmmn:entryCriterion", namespaces=ns): 
            # print("- sentry")              
            sentry = root.findall(f".//cmmn:sentry[@id='{entryCrit.attrib['sentryRef']}']", namespaces=ns)[0]
            
            sentryObj = {
                'id': entryCrit.attrib['id'],
                'ref': sentry.attrib['id'],
                'items': [],
                'conditions': []
            }
            itemObj['sentries']['entry'].append(sentryObj)
            
            itemParts = sentry.findall(".//cmmn:planItemOnPart", namespaces=ns)
            for itemPart in itemParts:
                sentryItemObj = { 'id': itemPart.attrib['id'] }
                sourcePlanItem = root.findall(f".//cmmn:planItem[@id='{itemPart.attrib['sourceRef']}']", namespaces=ns)[0]
                sourceDefRef = sourcePlanItem.attrib['definitionRef']
                sentryItemObj['source'] = sourceDefRef
                # print("source:", sourceDefRef)
                
                events = itemPart.findall(".//cmmn:standardEvent", namespaces=ns)
                if len(events) > 0:
                    eventLabel = events[0].text
                    sentryItemObj['event'] = eventLabel
                    # print("event:", eventLabel)
            
                sentryObj['items'].append(sentryItemObj)
            
            associations = root.findall(f".//cmmn:association[@sourceRef='{entryCrit.attrib['id']}']", namespaces=ns)
            for association in associations:
                condItemObj = { 'id': association.attrib['targetRef'] }
                textAnnotations = root.findall(f".//cmmn:textAnnotation[@id='{association.attrib['targetRef']}']", namespaces=ns)
                if len(textAnnotations) > 0:
                    textAnnotation = textAnnotations[0].findall(".//cmmn:text", namespaces=ns)[0].text
                    # print("condition:", textAnnotation)
                    condItemObj['text'] = textAnnotation
                    sentryObj['conditions'].append(condItemObj)
                    
        # print("")
    
    for stage, itemObj in stages:
        itemObj['children'] = []
        for childPlanItem in stage.findall(".//cmmn:planItem", namespaces=ns):
            child = refToObj[childPlanItem.attrib['definitionRef']]['label']
            itemObj['children'].append(child)
    
    return labelToObj