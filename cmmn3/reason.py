from rdflib import Graph, RDF
from rdflib.collection import Collection
import os, re
import pandas as pd
from util import run
from cmmn3.parse import parseOut
from cmmn3.ns import CM

def reasonAll(modelPath, obsPath, n3Path, printerr=False):
    allErrors = []; allFinals = []

    # for obsFile in sorted(os.listdir(obsFolder)):
        # case = int(re.search("obs(\\d+)\.ttl", obsFile).group(1))
        # obsPath = os.path.join(obsFolder, obsFile)
        # print(obsPath)
        
    with open(obsPath, 'r') as fh:
        for count, singleObs in enumerate(fh): # yeah, yeah ...      
            if count % 10 == 0:
                print("count:", count)
            if count == 100: # and count % 100 == 0:
                break
            
            # i know!
            case = re.search("\(.*\)\s.*?\s\"(.*)\" \.", singleObs).group(1)
            # print(case)
            
            singleObsPath = os.path.join(os.path.dirname(obsPath), "single_obs.ttl")
            with open(singleObsPath, 'w') as fh2:
                fh2.write(singleObs)

            out = reason(modelPath, singleObsPath, n3Path, printerr=printerr)
            # print(out)
            
            errors, finals = parseOut(out, case)
            allErrors.extend(errors); allFinals.extend(finals)
        
    errorDf = pd.DataFrame(columns=['case', 'item', 'error', 'type'], data=allErrors)
    finalDf = pd.DataFrame(columns=['case', 'item', 'type'], data=allFinals)
        
    return errorDf, finalDf


def reason(modelPath, obsPath, n3Path, printerr=False):
    out = run(['eye', modelPath, obsPath, 
               os.path.join(n3Path, 'graph.n3'), 
               os.path.join(n3Path, 'state.n3'), 
               os.path.join(n3Path, 'workflow.n3'), 
               os.path.join(n3Path, 'run.n3'), 
            '--nope', '--pass-only-new'], printerr=printerr, get_time=False)
    return out