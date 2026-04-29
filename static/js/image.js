let isImageLoadingInitialized = false;

export function initImageLoading(root = document) {
    if (root === document) {
        if (isImageLoadingInitialized) return;
        isImageLoadingInitialized = true;
    }

    root.addEventListener('load', handleImageLoaded, true);
    root.addEventListener('error', handleImageError, true);
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
