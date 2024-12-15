import {getContent} from '/js/file.js'

const routes = {
    '/': 'html/home.html',
    'about': 'html/about.html',
    'contact': 'html/contact.html',
};

function loadPage(path, to_element='content', css=true) {
    let content_path=routes[path] || routes['/']
    console.log('content_path',content_path)
    load(to_element, content_path)

    if(css){
        let css_path = 'css/' + (path || 'home') +'.css'
        console.log('css_path',css_path)
        let link = document.getElementById('cssCustom')
        getContent(css_path).then(([content, status]) =>{
            if(status==200)
                link.setAttribute('href', content)
            else
                throw new Error(`Error loading ${id}: ${content}`)
        })
    }
}

function load(id, path='', default_enxtension='html'){
    const element_id = document.getElementById(id)

    if(!path)
        path = default_enxtension+'/'+id+'.'+default_enxtension

    console.log('path ', path)

    getContent(path).then(([content, status]) =>{
        if(status==200)
            element_id.innerHTML = content
        else
            throw new Error(`Error loading ${id}: ${content}`)
    })
}

function navigateTo(path) {
    window.history.pushState({}, path, window.location.origin + '#' + path);
    console.log("nav ", path)
    loadPage(path);
}

window.addEventListener('DOMContentLoaded', () => {
    load('header')
    navigateTo(window.location.pathname)
    load('footer')
});
