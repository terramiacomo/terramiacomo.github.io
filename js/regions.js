const regions = [
    { name: "Abruzzo", count: 4 },
    { name: "Basilicata", count: 13 },
    { name: "Calabria", count: 50 },
    { name: "Campania", count: 1 },
    { name: "Emilia Romagna", count: 2 },
    { name: "Puglia", count: 21 },
    { name: "Liguria", count: 9 },
    { name: "Lombardia", count: 29 },
    { name: "Marche", count: 4 },
    { name: "Piemonte", count: 8 },
    { name: "Sardegna", count: 7 },
    { name: "Sicilia", count: 33 },
    { name: "Toscana", count: 8 },
    { name: "Trentino", count: 12 },
    { name: "Umbria", count: 7 },
    { name: "Veneto", count: 5 }
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
                <a href="images/regions/${region.name}/${i}@2x.jpeg" class="gallery-small-items__item-thumb glightbox">
                    <img src="images/regions/${region.name}/${i}.jpeg"
                         srcset="images/regions/${region.name}/${i}.jpeg" alt="${region.name} photo ${i}">
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