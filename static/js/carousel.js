document.addEventListener("DOMContentLoaded", () => {
    const images = document.querySelectorAll(".carousel .image");
    const bullets = document.querySelectorAll(".bullets span");
    const textGroup = document.querySelector(".text-group");
    const texts = [
        ["Real-Time Stock Price Analyzer"],
        ["EXCLUSIVELY FOR DSA"],
        ["Meet the Team"]
    ];
    let currentIndex = 0;

    const updateCarousel = (index) => {
        images.forEach((img) => img.classList.remove("show"));
        bullets.forEach((bullet) => bullet.classList.remove("active"));

        images[index].classList.add("show");
        bullets[index].classList.add("active");

        textGroup.innerHTML = '';
        texts[index].forEach(text => {
            const h2 = document.createElement('h2');
            h2.textContent = text;
            textGroup.appendChild(h2);
        });
    };

    bullets.forEach((bullet, index) => {
        bullet.addEventListener("click", () => {
            currentIndex = index;
            updateCarousel(currentIndex);
        });
    });

    setInterval(() => {
        currentIndex = (currentIndex + 1) % images.length;
        updateCarousel(currentIndex);
    }, 3000);
});
