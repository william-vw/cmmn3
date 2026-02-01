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

    for _, item, itemId, itemState in finals:
        showStates.append(f"showState('{itemId}', '{itemState.lower()}', canvas, overlays);")
        
    for _, item, itemId, itemError, itemState  in errors:
        itemObj = itemObjs[item]
        
        match (itemError):
            case 'readyToCompleted':
                showStates.append(f"showState('{itemId}', 'error', canvas, overlays);")
                for sentry in itemObj['sentries']['entry']:
                    showStates.append(f"showState('{sentry['id']}', 'sentryViolated', canvas, overlays);")
                    
            case 'inactiveToCompleted':
                showStates.append(f"showState('{itemId}', 'error', canvas, overlays);")
            
            case 'mandatoryNotDone':
                showStates.append(f"showState('{itemId}', 'error', canvas, overlays);")
                showStates.append(f"showState('{itemId}', 'firstSymbolViolated', canvas, overlays);")
                
            case 'nonRepetitiveMultipleCompleted':
                showStates.append(f"showState('{itemId}', 'error', canvas, overlays);")
                clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                showStates.append(f"showState('{itemId}', '{clsName}', canvas, overlays);")
                extraMarkers.append(f"'{itemId}': {{ 'isRepeatable': true }}")
                
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