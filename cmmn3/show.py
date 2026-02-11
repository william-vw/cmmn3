import os
from util import run

orViewerPath = "js/viewer-or.html"; newViewerPath = "js/viewer.html"
    
def showCase(out, case, itemObjs, cmmnXmlPath, imgPath):
    errors, finals = out
    
    def getCaseUpdates(errors, finals, itemObjs):
        showStates = []; extraMarkers = []
        
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
                        
        return showStates, extraMarkers, []
    
    # filter by case
    errors = [ row.to_list() for _, row in errors[errors['case']==case].iterrows() ]
    finals = [ row.to_list() for _, row in finals[finals['case']==case].iterrows() ]
    
    vis = getCaseUpdates(errors, finals, itemObjs)
    
    updateViewer(vis, cmmnXmlPath)
    return runViewer("js", imgPath, printerr=True)


def showErrors(errors, itemObjs, cmmnXmlPath, imgPath):

    def getErrorUpdates(errors, itemObjs):
        showStates = []; extraMarkers = []; extraCss = []

        for _, item, totalPerc, itemErrors  in errors:
            itemObj = itemObjs[item]
            visId = itemObj['id']
            
            addPercState(visId, 'error', totalPerc, showStates, extraCss)
            
            for itemError, errorPerc in itemErrors:
                match (itemError):
                    case 'readyToCompleted':
                        for sentry in itemObj['sentries']['entry']:
                            addPercState(sentry['id'], 'sentryViolated', errorPerc, showStates, extraCss)
                            
                    case 'inactiveToCompleted':
                        pass
                    
                    case 'mandatoryNotDone':
                        addPercState(visId, 'firstSymbolViolated', errorPerc, showStates, extraCss)
                        
                    case 'nonRepetitiveMultipleCompleted':
                        clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                        addPercState(visId, clsName, errorPerc, showStates, extraCss)
                        extraMarkers.append(f"'{visId}': {{ 'isRepeatable': true }}")
            
        return showStates, extraMarkers, extraCss

    vis = getErrorUpdates(errors, itemObjs)

    updateViewer(vis, cmmnXmlPath)
    return runViewer("js", imgPath, printerr=True)


def updateViewer(vis, xmlPath):
    global orViewerPath, newViewerPath
    
    showStates, extraMarkers, extraCss = vis
                
    showStatesJs = "\n".join(showStates)
    # print(showStatesJs)
    extraMarkersJs = ",".join(extraMarkers)
    extraMarkersJs = f"window.extraMarkers = {{ { extraMarkersJs } }}"
    # print(extraMarkersJs)
    extraCssCode = "\n".join(extraCss)
    # print(extraCssCode)

    with open(orViewerPath, 'r') as f:
        html = f.read()
        
    with open(newViewerPath, 'w') as htmlFile , open(xmlPath, 'r') as xmlFile:
        # avoid CORS exception when trying to load diagram XML
        # just directly include in the file!
        cmmnXml = xmlFile.read()
        html = html.replace("<cmmnXmlPlaceholder>", cmmnXml)
        html = html.replace("<extraMarkersPlaceholder>", extraMarkersJs)
        html = html.replace("<showStatesPlaceholder>", showStatesJs)
        html = html.replace("<cssPlaceholder>", extraCssCode)
        htmlFile.write(html)
        
        
def runViewer(appJsPath, imgPath, printerr=False):
    global newViewerPath
    
    return run(['node', os.path.join(appJsPath, "app.js"), newViewerPath, imgPath], get_time=False, printerr=printerr)

def addPercState(visId, or_cls, perc, showStates, extraCss):
    perc_light = 100 - perc
    cls = f".{or_cls}_{perc_light}"
    
    showStates.append(f"showState('{visId}', {cls}, canvas, overlays);")
    extraCss.append(f".{cls} .djs-visual > :nth-child(1) {{ stroke: hsl(0, 100%, {perc_light}%) }}")