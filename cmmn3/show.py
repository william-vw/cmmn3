import os
from util import run

def visualize(reasonOut, itemObjs, cmmnXmlPath, imgPath):
    orViewerPath = "js/viewer-or.html"; newViewerPath = "js/viewer.html"
    
    errors, finals = reasonOut
    updateViewer(errors, finals, itemObjs, orViewerPath, newViewerPath, cmmnXmlPath)
    return runViewer("js", newViewerPath, imgPath, printerr=True)

def runViewer(appJsPath, viewerPath, imgPath, printerr=False):
    return run(['node', os.path.join(appJsPath, "app.js"), viewerPath, imgPath], get_time=False, printerr=printerr)

def updateViewer(errors, finals, itemObjs, orViewerPath, newViewerPath, xmlPath):
    showStates = []
    extraMarkers = []

    for label, itemState in finals.items():
        showStates.append(f"showState('{itemState['item']}', '{itemState['state'].lower()}', canvas, overlays);")
        
    for label, itemError  in errors.items():
        item = itemError['item']
        error = itemError['error']
        
        itemObj = itemObjs[label]
        match (error):
            case 'readyToCompleted':
                showStates.append(f"showState('{item}', 'error', canvas, overlays);")
                for sentry in itemObj['sentries']['entry']:
                    showStates.append(f"showState('{sentry['id']}', 'sentryViolated', canvas, overlays);")
                    
            case 'inactiveToCompleted':
                showStates.append(f"showState('{item}', 'error', canvas, overlays);")
            
            case 'mandatoryLastNotDone':
                showStates.append(f"showState('{item}', 'error', canvas, overlays);")
                showStates.append(f"showState('{item}', 'firstSymbolViolated', canvas, overlays);")
                
            case 'nonRepetitiveMultipleCompleted':
                showStates.append(f"showState('{item}', 'error', canvas, overlays);")
                clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                showStates.append(f"showState('{item}', '{clsName}', canvas, overlays);")
                extraMarkers.append(f"'{item}': {{ 'isRepeatable': true }}")
                
    showStatesJs = "\n".join(showStates)
    # print(showStatesJs)
    extraMarkersJs = ",".join(extraMarkers)
    extraMarkersJs = f"window.extraMarkers = {{ { extraMarkersJs } }}"
    # print(extraMarkersJs)

    with open(orViewerPath, 'r') as f:
        html = f.read()
        
    with open(newViewerPath, 'w') as htmlFile , open(xmlPath, 'r') as xmlFile:
        # avoid CORS exception when trying to load diagram XML
        # just directly include in the file!
        cmmnXml = xmlFile.read()
        html = html.replace("<cmmnXmlPlaceholder>", cmmnXml)
        
        html = html.replace("<extraMarkersPlaceholder>", extraMarkersJs)
        html = html.replace("<showStatesPlaceholder>", showStatesJs)
        htmlFile.write(html)