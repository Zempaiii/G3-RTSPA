document.addEventListener("DOMContentLoaded", () => {
    const images = document.querySelectorAll(".carousel .image");
    const bullets = document.querySelectorAll(".bullets span");
    let currentIndex = 0;

    const updateCarousel = (index) => {
        images.forEach((img) => img.classList.remove("show"));
        bullets.forEach((bullet) => bullet.classList.remove("active"));

        images[index].classList.add("show");
        bullets[index].classList.add("active");
    };

    bullets.forEach((bullet, index) => {
        bullet.addEventListener("click", () => {
            currentIndex = index;
            updateCarousel(currentIndex);
        });
    });
});
