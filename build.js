({
    appDir: 'static/js',
    baseUrl: '.',
    dir: 'static/js-compiled',
    mainConfigFile: 'static/js/config.js',
    // This prevents unwanted file in the baseUrl from being copied to the
    // compiled/ folder before optimization. Currently there's no way to tell
    // requirejs to only copy javascript files
    fileExclusionRegExp: /(^\.|.*test.*|compiled|css)(?!\.js$)/,
    /*
     * List the modules that will be optimized. All their immediate and deep
     * dependencies will be included in the module's file when the build is
     * done. A minimum module entry is {name: "module_name"}.
     */
    modules: [
        {
            name: 'config',
            include: [
                'lib/require',
                'lib/modernizr.min',
                'lib/underwood',

                // //controllers
                'StoryDetail',
                'SuiteDetail',
                'ConversationDetail',
                'LinkDetail',
                'NavDetail',
                'ExploreDetail',
                'StaticDetail',
                'AdminDetail',
                'UserDetail',

                //mains
                'main/PageController',
                'suiteio',
                'main/ads',
                'main/AdsManager',
                'hb',
                'main'
            ]
        }
    ],
    // generateSourceMaps: true,
    optimizeCss: "None",
    /*
     * How to optimize all the JS files in the build output directory.
     * Right now only the following values are supported:
     * - "uglify": Uses UglifyJS to minify the code.
     * - "uglify2": Uses UglifyJS2.
     * - "closure": Uses Google's Closure Compiler in simple optimization
     * mode to minify the code. Only available if REQUIRE_ENVIRONMENT is "rhino" (the default).
     * - "none": No minification will be done.
     */
    // optimize: "none",
    optimize: "uglify2",
    
    /*
     * By default, comments that have a license in them are preserved in the
     * output. However, for a larger built files there could be a lot of
     * comment files that may be better served by having a smaller comment
     * at the top of the file that points to the list of all the licenses.
     * This option will turn off the auto-preservation, but you will need
     * work out how best to surface the license information.
     */
    preserveLicenseComments: false,
    
    /*
     * The default behaviour is to optimize the build layers (the "modules"
     * section of the config) and any other JS file in the directory. However, if
     * the non-build layer JS files will not be loaded after a build, you can
     * skip the optimization of those files, to speed up builds. Set this value
     * to true if you want to skip optimizing those other non-build layer JS
     * files.
     */
    skipDirOptimize: true
})