/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        interviewer: '#818cf8',
        interviewee: '#34d399',
      },
      typography: {
        invert: {
          css: {
            '--tw-prose-bold': '#818cf8',
            '--tw-prose-bullets': '#6366f1',
          },
        },
      },
      keyframes: {
        fadeSlide: {
          from: { opacity: 0, transform: 'translateY(6px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        blink: {
          '50%': { opacity: 0 },
        },
        pulseDot: {
          '0%,100%': { opacity: 1 },
          '50%':      { opacity: 0.2 },
        },
      },
      animation: {
        fadeSlide: 'fadeSlide 0.2s ease-out',
        blink:     'blink 1s step-start infinite',
        pulseDot:  'pulseDot 1.2s ease-in-out infinite',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
