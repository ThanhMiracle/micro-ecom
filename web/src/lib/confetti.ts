import confetti from "canvas-confetti";

export function candyConfetti() {
  const end = Date.now() + 900;
  const frame = () => {
    confetti({
      particleCount: 8,
      startVelocity: 22,
      spread: 70,
      ticks: 140,
      origin: { x: Math.random(), y: 0.2 },
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  };
  frame();
}
