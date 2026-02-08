module.exports = {
  plugins: [
    {
      plugin: {
        overrideWebpackConfig: ({ webpackConfig }) => {
          const ForkTsCheckerIndex = webpackConfig.plugins.findIndex(
            (p) => p && p.constructor && p.constructor.name === 'ForkTsCheckerWebpackPlugin'
          );
          if (ForkTsCheckerIndex !== -1) {
            webpackConfig.plugins.splice(ForkTsCheckerIndex, 1);
          }
          return webpackConfig;
        },
      },
    },
  ],
};
