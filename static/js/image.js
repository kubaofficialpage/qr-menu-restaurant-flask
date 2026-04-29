let isImageLoadingInitialized = false;

export function initImageLoading(root = document) {
    if (root === document) {
        if (isImageLoadingInitialized) return;
        isImageLoadingInitialized = true;
    }

    root.addEventListener('load', handleImageLoaded, true);
    root.addEventListener('error', handleImageError, true);
}

export function ensureImageSpinner(image, spinnerClass = "image-spinner") {
    const previous = image.previousElementSibling;
    if (previous?.classList.contains("image-spinner")) return;

    const spinner = document.createElement("div");
    spinner.className = spinnerClass;
    image.before(spinner);
}

export function syncMenuImageElement(image, src, alt = "", spinnerClass = "image-spinner") {
    if (!image) return;
    if (image.dataset.imageSrc === src) return;

    image.dataset.imageSrc = src;
    image.classList.remove("is-loaded");
    image.src = src;
    image.alt = alt ?? "";
    ensureImageSpinner(image, spinnerClass);
}

function handleImageLoaded(e) {
    const image = e.target;
    if (!(image instanceof HTMLImageElement) || !image.classList.contains("menu-image")) return;

    image.classList.add("is-loaded");
    image.previousElementSibling?.classList.contains("image-spinner") && image.previousElementSibling.remove();
}

function handleImageError(e) {
    const image = e.target;
    if (!(image instanceof HTMLImageElement) || !image.classList.contains("menu-image")) return;

    image.previousElementSibling?.classList.contains("image-spinner") && image.previousElementSibling.remove();
    image.remove();
}
