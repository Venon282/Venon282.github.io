// router.js

const routes = {
    '/': 'home.html',
    '/about': 'about.html',
    '/contact': 'contact.html',
};

function loadPage(path) {
    const contentElement = document.getElementById('content');
    const page = routes[path] || routes['/'];
    
    fetch(page)
        .then(response => response.text())
        .then(html => {
            contentElement.innerHTML = html;
        })
        .catch(error => console.error('Error loading page:', error));
}

function setupRouter() {
    const navbar = document.getElementById('navbar');
    navbar.innerHTML = `
        <a href="#/" onclick="navigateTo('/')">Home</a>
        <a href="#/about" onclick="navigateTo('/about')">About</a>
        <a href="#/contact" onclick="navigateTo('/contact')">Contact</a>
    `;

    window.onpopstate = () => loadPage(window.location.pathname);
}

function navigateTo(path) {
    window.history.pushState({}, path, window.location.origin + path);
    loadPage(path);
}

window.addEventListener('DOMContentLoaded', () => {
    setupRouter();
    loadPage(window.location.pathname);
});
