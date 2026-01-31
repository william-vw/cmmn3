from util import run
import os


def reason(modelPath, obsPath, n3Path, printerr=False):
    out = run(['eye', modelPath, obsPath, 
               os.path.join(n3Path, 'graph.n3'), 
               os.path.join(n3Path, 'state.n3'), 
               os.path.join(n3Path, 'workflow.n3'), 
               os.path.join(n3Path, 'run.n3'), 
            '--nope', '--pass-only-new'], printerr=printerr)
    return out
