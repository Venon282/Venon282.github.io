import File from '/js/file.js'

const routes = {
    '':                     {'html': 'html/home.html', 'css':'css/home.css'},
    'home':                 {'html': 'html/home.html', 'css':'css/home.css'},
    'about':                {'html': 'html/about.html', 'css':'css/about.css'},
    'contact':              {'html': 'html/contact.html', 'css':'css/contact.css'},
    'recipe':               {'html': 'html/recipe.html', 'css':'css/recipe.css'},
    'recipe/new_recipe':    {'html': 'html/new_recipe.html', 'css':'css/new_recipe.css'}
};

function loadPage(path, to_element='content', css=true) {
    const content_path=routes[path] || routes['']

    // delete the old scipts
    const old_scripts = document.getElementById(to_element).querySelectorAll('script');
    old_scripts.forEach(old_script => old_script.remove())

    load(to_element, content_path['html'])

    if(css){
        let link = document.getElementById('cssCustom')
        link.setAttribute('href', content_path['css'])
    }
}

function load(id, path='', default_enxtension='html'){
    const element_id = document.getElementById(id)

    if(!path)
        path = default_enxtension+'/'+id+'.'+default_enxtension

    File.getContent(path).then(([content, status]) =>{
        if(status==200){
            element_id.innerHTML = content
            // After loading the content, we need to execute the script
            const scripts = element_id.querySelectorAll('script');
            scripts.forEach(script => {
                const newScript = document.createElement('script')
                newScript.type = script.type || 'text/javascript'
                newScript.textContent = `(function(){${script.textContent}})()`
                element_id.appendChild(newScript);
            });
        }else
            throw new Error(`Error loading ${id}: ${content}`)
    })
}

function navigateTo(path) {
    console.log("nav to", path, 'origin ',window.location.origin)
    window.location.hash = path
    //window.history.pushState({}, path, window.location.origin + '/' + path)
    loadPage(path);
}

window.navigateTo = navigateTo // Attach navigateTo to window

window.addEventListener('DOMContentLoaded', () => {
    load('header')
    const path = window.location.hash.slice(1) || '' //window.location.pathname.split('/')[1]
    navigateTo(path)
    load('footer')
});
