const regions = [
    { name: "calabria", count: 43 },
    { name: "puglia", count: 10 },
    { name: "lombardia", count: 15 },
    { name: "sardegna", count: 7 },
    { name: "sicilia", count: 33 },
    { name: "trentino", count: 0 },
    { name: "umbria", count: 7 },
    { name: "veneto", count: 4 }
];

const galleryContainer = document.getElementById('gallery');

regions.forEach(region => {
    // 1. Skip if the value is 0
    if (region.count === 0) return;

    // 2. Create the Header HTML
    let regionHTML = `
        <div class="row s-gallery__header">
            <div class="column xl-12 section-header-wrap">
                <h3 class="text-display-title">${region.name.toUpperCase()}</h3>
            </div>
        </div>
        <div class="gallery-small-items grid-cols grid-cols--wrap">`;

    // 3. Loop to create the individual image items
    for (let i = 1; i <= region.count; i++) {
        regionHTML += `
            <div class="gallery-small-items__item grid-cols__column">
                <a href="images/regions/${region.name}/${i}@2x.jpg" class="gallery-small-items__item-thumb glightbox">
                    <img src="images/regions/${region.name}/${i}.jpg"
                         srcset="images/regions/${region.name}/${i}.jpg" alt="${region.name} photo ${i}">
                </a>
            </div>`;
    }

    // 4. Close the gallery items div
    regionHTML += `</div>`;

    // 5. Append the full region block to the gallery section
    galleryContainer.innerHTML += regionHTML;
});

// 6. Reinitialize GLightbox for dynamically added elements
if (typeof GLightbox !== 'undefined') {
    GLightbox({
        selector: '.glightbox',
        zoomable: false,
        touchNavigation: true,
        loop: false,
        autoplayVideos: true
    });
}