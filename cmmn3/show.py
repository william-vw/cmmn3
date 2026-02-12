import os
from util import run, minmaxnorm

orViewerPath = "js/viewer-or.html"; newViewerPath = "js/viewer.html"
    
def showCase(out, case, itemObjs, cmmnXmlPath, imgPath):
    errors, finals = out
    
    def getCaseUpdates(errors, finals, itemObjs):
        vis = { 'showStates': set(), 'extraMarkers': set(), 'extraCss': set() }
        
        for _, item, itemState in finals:
            visId = itemObjs[item]['id']
            addState(visId, itemState.lower(), vis)
        
        for _, item, itemError, itemState  in errors:
            itemObj = itemObjs[item]
            visId = itemObj['id']
            
            match (itemError):
                case 'readyToCompleted':
                    addState(visId, 'error', vis)
                    for sentry in itemObj['sentries']['entry']:
                        addState(sentry['id'], 'sentryViolated', vis)
                        
                case 'inactiveToCompleted':
                    addState(visId, 'error', vis)
                
                case 'mandatoryNotDone':
                    addState(visId, 'error', vis)
                    addState(visId, 'firstSymbolViolated', vis)
                    
                case 'nonRepetitiveMultipleCompleted':
                    addState(visId, 'error', vis)
                    
                    clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                    addState(visId, clsName, vis, repeatableMarker=True)
                        
        return vis
    
    # filter by case
    errors = [ row.to_list() for _, row in errors[errors['case']==case].iterrows() ]
    finals = [ row.to_list() for _, row in finals[finals['case']==case].iterrows() ]
    
    vis = getCaseUpdates(errors, finals, itemObjs)
    
    updateViewer(vis, cmmnXmlPath)
    return runViewer("js", imgPath, printerr=True)


def showErrors(out, itemObjs, cmmnXmlPath, imgPath):

    def aggregate_errors(out):
        errors, finals = out
        
        num_cases = len(finals['case'].unique())
        item_cnt = errors.groupby('item').apply(lambda g: round(len(g) / num_cases * 100)).clip(0, 100).reset_index(name='total_perc')
        error_cnt =  errors.groupby([ 'item', 'error' ]).apply(lambda g: round(len(g) / num_cases * 100)).clip(0, 100).reset_index(name='error_perc')

        all_errors = item_cnt.merge(error_cnt)
        all_errors

        return ( ( g.iloc[0]['item'], g.iloc[0]['total_perc'], ( ( gr['error'], gr['error_perc'] ) for i2, gr in g.iterrows() ) ) for i, g in all_errors.groupby('item') )

    def getErrorUpdates(errors, itemObjs):
        vis = { 'showStates': set(), 'extraMarkers': set(), 'extraCss': set() }

        for item, totalPerc, itemErrors in errors:
            itemObj = itemObjs[item]
            visId = itemObj['id']
            
            addPercState(visId, 'error', totalPerc, vis)
            
            for itemError, errorPerc in itemErrors:
                match (itemError):
                    case 'readyToCompleted':
                        for sentry in itemObj['sentries']['entry']:
                            addPercState(sentry['id'], 'sentryViolated', errorPerc, vis)
                            
                    case 'inactiveToCompleted':
                        pass
                    
                    case 'mandatoryNotDone':
                        addPercState(visId, 'firstSymbolViolated', errorPerc, vis)
                        
                    case 'nonRepetitiveMultipleCompleted':
                        clsName = 'secondSymbolViolated' if (itemObj['mandatory']) else 'firstSymbolViolated'
                        addPercState(visId, clsName, errorPerc, vis, repeatableMarker=True)
            
        return vis

    agg_errors = aggregate_errors(out)
    vis = getErrorUpdates(agg_errors, itemObjs)

    print(vis)

    updateViewer(vis, cmmnXmlPath)
    return runViewer("js", imgPath, printerr=True)


def updateViewer(vis, xmlPath):
    global orViewerPath, newViewerPath
    
    showStates, extraMarkers, extraCss = vis.values()
                
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

def addState(visId, cls, vis, repeatableMarker=False):
    showStates, extraMarkers, _ = vis.values()
    
    showStates.add(f"showState('{visId}', {cls}, canvas, overlays);")
    if repeatableMarker:
        extraMarkers.add(f"'{visId}': {{ 'isRepeatable': true }}")

def addPercState(visId, or_cls, perc, vis, repeatableMarker=False):
    showStates, extraMarkers, extraCss = vis.values()
    
    match(or_cls):
        case 'firstSymbolViolated':
            nth_child = 3
            stroke_width = 3
        case 'secondSymbolViolated':
            nth_child = 4
            stroke_width = 3
        case _:
            nth_child = 1
            stroke_width = 5
    
    perc_light = 100 - perc
    norm_light = minmaxnorm(0, 100, 40, 80, perc_light)
    
    cls = f"{or_cls}_{perc_light}"
    extraCss.add(f".{cls} .djs-visual > :nth-child({nth_child}) {{ stroke: hsl(0, 100%, {norm_light}%) !important; stroke-width: {stroke_width}px !important }}")
    showStates.add(f"showState('{visId}', '{cls}', canvas, overlays);")
    if repeatableMarker:
        extraMarkers.add(f"'{visId}': {{ 'isRepeatable': true }}")