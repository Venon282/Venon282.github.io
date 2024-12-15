import getContent from '/js/file.js'

const routes = {
    '/': 'html/home.html',
    '/about': 'html/about.html',
    '/contact': 'html/contact.html',
};

function loadPage(path, to_element='content', css=true) {
    load(id=to_element, path=routes[path] || routes['/'])

    if(css){
        path = 'css' + (path || 'home') +'.css'
        link = document.getElementById('cssCustom')
        const [content, status] = getContent(path)
        if(status==200)
            link.setAttribute('href', content)
        else
            throw new Error(`Error loading ${id}: ${content}`)
    }
}

function load(id, path='', default_enxtension='html'){
    const element_id = document.getElementById(id)

    if(!path)
        path = default_enxtension+'/'+id+'.'+default_enxtension

    const [content, status] = getContent(path)

    if(status==200)
        element_id.innerHTML = content
    else
        throw new Error(`Error loading ${id}: ${content}`)

}

function navigateTo(path) {
    window.history.pushState({}, path, window.location.origin + path);
    loadPage(path);
}

window.addEventListener('DOMContentLoaded', () => {
    window.onpopstate = () => loadPage(window.location.pathname)
    load(id='header')
    loadPage(path=window.location.pathname)
    load(id='footer')
});
