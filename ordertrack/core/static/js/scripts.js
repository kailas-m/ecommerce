// Carousel functionality
const carousel = document.querySelector('.carousel');
const carouselInner = document.querySelector('.carousel-inner');
const carouselItems = document.querySelectorAll('.carousel-item');
const dots = document.querySelectorAll('.carousel-dots .dot');
const prevBtn = document.querySelector('.carousel-prev');
const nextBtn = document.querySelector('.carousel-next');
let currentIndex = 0;
let carouselInterval;

function showSlide(index) {
    if (index >= carouselItems.length) index = 0;
    if (index < 0) index = carouselItems.length - 1;
    carouselInner.style.transform = `translateX(-${index * 100}%)`;
    dots.forEach(dot => dot.classList.remove('active'));
    dots[index].classList.add('active');
    currentIndex = index;
}

function goToSlide(index) {
    showSlide(index);
    resetCarouselInterval();
}

function pauseCarousel() {
    clearInterval(carouselInterval);
}

function resumeCarousel() {
    resetCarouselInterval();
}

function resetCarouselInterval() {
    clearInterval(carouselInterval);
    carouselInterval = setInterval(() => showSlide(currentIndex + 1), 5000);
}

if (carousel) {
    prevBtn.addEventListener('click', () => {
        showSlide(currentIndex - 1);
        resetCarouselInterval();
    });

    nextBtn.addEventListener('click', () => {
        showSlide(currentIndex + 1);
        resetCarouselInterval();
    });

    dots.forEach(dot => {
        dot.addEventListener('click', () => goToSlide(parseInt(dot.dataset.slide)));
    });

    carousel.addEventListener('mouseenter', pauseCarousel);
    carousel.addEventListener('mouseleave', resumeCarousel);

    resetCarouselInterval();
}

// Countdown timer
const timer = document.querySelector('.countdown-timer');
if (timer) {
    const endTime = new Date(timer.dataset.endTime).getTime();
    function updateTimer() {
        const now = new Date().getTime();
        const distance = endTime - now;
        if (distance < 0) {
            timer.innerHTML = 'Deal Ended!';
            return;
        }
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        timer.querySelector('.timer-days').textContent = days.toString().padStart(2, '0');
        timer.querySelector('.timer-hours').textContent = hours.toString().padStart(2, '0');
        timer.querySelector('.timer-minutes').textContent = minutes.toString().padStart(2, '0');
        timer.querySelector('.timer-seconds').textContent = seconds.toString().padStart(2, '0');
    }
    updateTimer();
    setInterval(updateTimer, 1000);
}