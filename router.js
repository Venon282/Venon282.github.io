// router.js

const routes = {
    '/': 'html/home.html',
    '/about': 'html/about.html',
    '/contact': 'html/contact.html',
};

function loadPage(path, to_element='content') {
    load(id=to_element, content=routes[path] || routes['/'])
}

function load(id, content='', default_enxtension='.html'){
    const element_id = document.getElementById(id)

    if(!content)
        content = id+default_enxtension

    fetch(content)
        .then(response => response.text())
        .tehn(html => {
            element_id.innerHTML = html
        })
        .catch(error => console.error('Error loading: ', id))
}

// function setupRouter() {
//     const navbar = document.getElementById('navbar');
//     navbar.innerHTML = `
//         <a href="#/" onclick="navigateTo('/')">Home</a>
//         <a href="#/about" onclick="navigateTo('/about')">About</a>
//         <a href="#/contact" onclick="navigateTo('/contact')">Contact</a>
//     `;

//     window.onpopstate = () => loadPage(window.location.pathname);
// }

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
