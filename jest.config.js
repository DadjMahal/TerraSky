module.exports = {
    testEnvironment: 'jsdom',
    testMatch: ['**/tests/**/*.test.js', '**/tests/**/*.spec.js', '**/tests/test_*.js'],
    testEnvironmentOptions: {
        url: 'http://localhost/',
    },
    verbose: true,
};
