// loading.js
const showLoading = () => {
    const loadingElement = document.createElement('div');
    loadingElement.classList.add('loading');

    const loadingIcon = document.createElement('div');
    loadingIcon.classList.add('loading-icon');

    loadingElement.appendChild(loadingIcon);

    document.body.appendChild(loadingElement);
};

const hideLoading = () => {
    const loadingElement = document.querySelector('.loading');

    if (loadingElement) {
        document.body.removeChild(loadingElement);
    }
};