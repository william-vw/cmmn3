import os, re
import pandas as pd
from util import run
from cmmn3.parse import parseOut

def reasonAll(modelPath, obsFolder, n3Path, itemObjs, printerr=False):
    allErrors = []; allFinals = []

    for obsFile in sorted(os.listdir(obsFolder)):
        case = int(re.search("obs(\\d+)\.ttl", obsFile).group(1))
        obsPath = os.path.join(obsFolder, obsFile)
        print(obsPath)

        out = reason(modelPath, obsPath, n3Path, printerr=printerr)
        # print(out)
        
        errors, finals = parseOut(out, case, itemObjs)
        allErrors.extend(errors); allFinals.extend(finals)
        
    errorDf = pd.DataFrame(columns=['case', 'item', 'itemId', 'error', 'type'], data=allErrors)
    finalDf = pd.DataFrame(columns=['case', 'item', 'itemId', 'type'], data=allFinals)
        
    return errorDf, finalDf


def reason(modelPath, obsPath, n3Path, printerr=False):
    out = run(['eye', modelPath, obsPath, 
               os.path.join(n3Path, 'graph.n3'), 
               os.path.join(n3Path, 'state.n3'), 
               os.path.join(n3Path, 'workflow.n3'), 
               os.path.join(n3Path, 'run.n3'), 
            '--nope', '--pass-only-new'], printerr=printerr)
    return out
