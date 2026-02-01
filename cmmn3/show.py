import os
from util import run

def visualize(out, case, itemObjs, cmmnXmlPath, imgPath):
    orViewerPath = "js/viewer-or.html"; newViewerPath = "js/viewer.html"
    
    errors, finals = out
    
    # filter by case
    errors = [ row.to_list() for _, row in errors[errors['case']==case].iterrows() ]
    finals = [ row.to_list() for _, row in finals[finals['case']==case].iterrows() ]
    
    updateViewer(errors, finals, itemObjs, orViewerPath, newViewerPath, cmmnXmlPath)
    return runViewer("js", newViewerPath, imgPath, printerr=True)

def runViewer(appJsPath, viewerPath, imgPath, printerr=False):
    return run(['node', os.path.join(appJsPath, "app.js"), viewerPath, imgPath], get_time=False, printerr=printerr)

def updateViewer(errors, finals, itemObjs, orViewerPath, newViewerPath, xmlPath):
    showStates = []
    extraMarkers = []

    for _, item, itemState in finals:
        visId = itemObjs[item]['id']
        showStates.append(f"showState('{visId}', '{itemState.lower()}', canvas, overlays);")
        
    for _, item, itemError, itemState  in errors:
        itemObj = itemObjs[item]
        visId = itemObj['id']
        
        match (itemError):
            case 'readyToCompleted':
                showStates.append(f"showState('{visId}', 'error', canvas, overlays);")
                for sentry in itemObj['sentries']['entry']:
                    showStates.append(f"showState('{sentry['id']}', 'sentryViolated', canvas, overlays);")
                    
            case 'inactiveToCompleted':
                showStates.append(f"showState('{visId}', 'error', canvas, overlays);")
            
            case 'mandatoryNotDone':
                showStates.append(f"showState('{visId}', 'error', canvas, overlays);")
                showStates.append(f"showState('{visId}', 'firstSymbolViolated', canvas, overlays);")
                
            case 'nonRepetitiveMultipleCompleted':
                showStates.append(f"showState('{visId}', 'error', canvas, overlays);")
                clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                showStates.append(f"showState('{visId}', '{clsName}', canvas, overlays);")
                extraMarkers.append(f"'{visId}': {{ 'isRepeatable': true }}")
                
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