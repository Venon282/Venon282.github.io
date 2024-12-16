import File from '/js/file.js'

const routes = {
    '': 'html/home.html',
    'about': 'html/about.html',
    'contact': 'html/contact.html',
    'recipe': 'html/recipe.html',
};

function loadPage(path, to_element='content', css=true) {
    let content_path=routes[path] || routes['']
    console.log('content_path',content_path)
    load(to_element, content_path)

    if(css){
        let css_path = `css/${path || 'home'}.css`
        console.log('css_path',css_path)
        let link = document.getElementById('cssCustom')
        link.setAttribute('href', css_path)
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
                const newScript = document.createElement('script');
                newScript.type = script.type || 'text/javascript';
                newScript.textContent = script.textContent;
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
