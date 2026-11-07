(image, unusedFrame) => {
    // Capture directly on this click; do not depend on Gradio's snapshot controls.
    const video = document.querySelector('#menu-camera video');
    if (!video || video.getClientRects().length === 0 || !video.srcObject) {
        return [image, ''];
    }
    if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
        return [null, 'camera-not-ready'];
    }
    try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        return [null, canvas.toDataURL('image/jpeg', 0.95)];
    } catch (error) {
        return [null, 'camera-capture-failed'];
    }
}
