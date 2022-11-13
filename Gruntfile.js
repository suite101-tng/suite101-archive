module.exports = function(grunt) {
    'use strict';
    // Project configuration.
    grunt.initConfig({
        handlebars: {
            compile: {
                options: {
                    amd: true,
                    namespace: 'Handlebars.templates',
                    processName: function(filepath) {
                        return filepath.replace(/static\/templates\/|\.handlebars\.html/ig, '');
                    }
                },
                files: {
                    'static/js/hb.js': 'static/templates/*.handlebars.html'
                }
            },
            compileServer: {
                options: {
                    amd: false,
                    namespace: 'Handlebars.templates',
                    node: true,
                    processName: function(filepath) {
                        return filepath.replace(/static\/templates\/|\.handlebars\.html/ig, '');
                    }
                },
                files: {
                    'node/hbs.js': 'static/templates/*.handlebars.html'
                }
            }
        },
        less: {
            production: {
                options: {
                    // paths: "static/less"
                    report: "min",
                    compress: true,
                    cleancss: true
                },
                files: {
                    'static/css/main.css': 'static/less/suite/main.less'
                }
            },
            dev: {
                options: {
                    sourceMap: true,
                    sourceMapRootpath: '/'
                },
                files: {
                    'static/css/main.css': 'static/less/suite/main.less'
                }
            }
        },
        watch: {
            less: {
                files: ['static/less/*.less', 'static/less/**/*.less'],
                tasks: ['less:dev']
            }
        }
    });
    grunt.loadNpmTasks('grunt-contrib-handlebars');
    grunt.loadNpmTasks('grunt-contrib-less');
    grunt.loadNpmTasks('grunt-contrib-watch');
    /** Grunt Tasks **/
    grunt.registerTask('default', ['less:dev', 'watch']);
    //grunt.registerTask('watch', ['watch:less']);
    grunt.registerTask('precompileHandlebars', ['handlebars:compile']);
    grunt.registerTask('makeLess', ['less:production']);
    grunt.registerTask('precompileHandlebarsServer', ['handlebars:compileServer']);
    grunt.registerTask('hbs', ['handlebars:compile', 'handlebars:compileServer']);
};