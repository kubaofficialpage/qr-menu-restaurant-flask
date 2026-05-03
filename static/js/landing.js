function initLandingPartnersTicker() {
    const track = document.getElementById("partnersTrack");
    if (!track) return;

    let offset = 0;
    let speed = 0.45;
    let raf = null;

    const tick = () => {
        const width = track.scrollWidth / 2;
        offset -= speed;
        if (Math.abs(offset) >= width) offset = 0;
        track.style.transform = `translate3d(${offset}px,0,0)`;
        raf = requestAnimationFrame(tick);
    };

    const stop = () => {
        if (raf) cancelAnimationFrame(raf);
        raf = null;
    };

    const start = () => {
        if (!raf) raf = requestAnimationFrame(tick);
    };

    let dragging = false;
    let startX = 0;
    let startOffset = 0;

    const onDown = (clientX) => {
        dragging = true;
        startX = clientX;
        startOffset = offset;
        stop();
    };

    const onMove = (clientX) => {
        if (!dragging) return;
        const dx = clientX - startX;
        offset = startOffset + dx;
        track.style.transform = `translate3d(${offset}px,0,0)`;
    };

    const onUp = () => {
        dragging = false;
        start();
    };

    track.addEventListener("pointerdown", (e) => {
        track.setPointerCapture?.(e.pointerId);
        onDown(e.clientX);
    });
    track.addEventListener("pointermove", (e) => onMove(e.clientX));
    track.addEventListener("pointerup", onUp);
    track.addEventListener("pointercancel", onUp);
    track.addEventListener("mouseenter", stop);
    track.addEventListener("mouseleave", () => {
        if (!dragging) start();
    });

    start();
}

initLandingPartnersTicker();
