// app.js

function initApp() {
    console.log('App initialized');
    
    // Example of dynamic content loading
    const contentElement = document.getElementById('content');
    
    // Example of setting default content
    contentElement.innerHTML = `
        <h2>Welcome to the Home Page</h2>
        <p>This is the default content of the homepage.</p>
    `;
}

function showAlert(message) {
    alert(message);
}

function handleFormSubmission(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    console.log('Form submitted with data:', data);
}

function setupEventListeners() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleFormSubmission);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});
