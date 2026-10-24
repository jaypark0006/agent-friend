export function createLifecycle(features,runtime) {
    const consumers=route=>{
        if(route==='devtools')return ['try','ws','camera'];
        if(route==='interact')return ['view'];
        if(route==='camera')return ['view','camera'];
        return features[route]?[route]:['view'];
    };
    let current=[];
    function leave(){for(const name of current)if(features[name]?.leave)features[name].leave();current=[];}
    return {
        enter(route){leave();runtime.route=route;current=consumers(route);for(const name of current)if(features[name]?.enter)features[name].enter();},
        suspend(){for(const name of current)if(features[name]?.suspend)features[name].suspend();},
        resume(){for(const name of current)if(features[name]?.resume)features[name].resume();},
        dispose(){for(const feature of Object.values(features))if(feature.dispose)feature.dispose();current=[];}
    };
}
