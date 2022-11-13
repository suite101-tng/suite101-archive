//template loader helper module
define(['jquery', 'handlebars'], function($, Handlebars) {
    'use strict';
    var _templateLoader = {

        requestedTemplates: {},

        _getSingleTemplate: function(templateName) {
            var $tmplsLot = this._getTemplatesLot(),
                tmpl = $tmplsLot.find('#' + templateName + '-template' ),
                tmplRaw,
                templateDeferred = $.Deferred(),
                compiledTmpl,
                self = this;
            if(!Handlebars.templates) {
                Handlebars.templates = {};
            }
            if(Handlebars.templates[templateName]) {
                //look for it in the Handlebars namespace
                templateDeferred.resolve(Handlebars.templates[templateName], null, templateName);
            } else if( tmpl.length ) {
                //look for it in the DOM
                tmplRaw = tmpl.html();
                if(typeof tmplRaw !== 'string') {
                    console.log(tmplRaw);
                }
                Handlebars.templates[templateName] = compiledTmpl = Handlebars.compile(tmplRaw);
                templateDeferred.resolve(compiledTmpl, tmplRaw, templateName);
            } else if(this.requestedTemplates[templateName]) {
                //this template has previously been requested and the ajax to grab it is pending
                return this.requestedTemplates[templateName];
            } else {
                //mark it as requested, so that subsequent request for the same template will not cause another ajax call
                this.requestedTemplates[templateName] = templateDeferred;
                //fire an ajax request to grab it
                this._getTmplOverAjax(templateName).done(function(response) {
                    var tmpl = self._ajaxHandler(response, templateName);
                    templateDeferred.resolve(tmpl, response, templateName);
                });
            }
            return templateDeferred.promise();
        },
        _getTmplOverAjax: function(templateName) {
            var templateURL = '/static/templates/' + templateName + '.handlebars.html';
            return $.ajax({
                url: templateURL
            });
        },
        _ajaxHandler: function(response, templateName) {
            var $templatesLot = this._getTemplatesLot();
            //put the markup in the dom
            var $scriptTag = $('<script>', {
                'id': templateName + '-template',
                'type': 'text/x-handlebars-template'
            }), tmpl;
            $scriptTag.text(response);
            $templatesLot.append( $scriptTag );
            //compile the template, cache it in the Handlebars namespace
            if(typeof response !== 'string') {
                console.log(response);
            }
            Handlebars.templates[templateName] = tmpl = Handlebars.compile(response);
            //resolve promise with template
            //remove itself from promise cache
            if(this.requestedTemplates[templateName]) {
                this.requestedTemplates[templateName] = null;
            }
            return tmpl;
        },

        _getTemplatesLot: function() {
            //grab the dom element that holds all templates, if it doesn't exist, create it
            var $templatesLot = $('#templates');
            if( !$templatesLot.length ) {
                $templatesLot = $('<div>', {'id': 'templates'});
                $('body').append($templatesLot);
            }
            return $templatesLot;
        },

        _getPartials: function(partials) {
            //given an array of template names, fetch each of them and register them as Handlebars partials
            var i, l, tmpPartial, partialName, partialsPromiseArr = [];
            for(i=0, l=partials.length ; i<l ; ++i) {
                partialName = partials[i];
                tmpPartial = this._getSingleTemplate(partialName);
                tmpPartial.done(this._registerPartial);
                partialsPromiseArr.push(tmpPartial);
            }
            return partialsPromiseArr;
        },

        _registerPartial: function(tmpl, html, tname) {
            Handlebars.registerPartial(tname, tmpl);
        },

        getTemplate: function(templateName, partials) {
            //exposed API method
            if(!partials || !partials.length) {
                //if no partials are requested, just fetch the template
                return this._getSingleTemplate(templateName);
            } else {
                var templateFullyLoaded = $.Deferred(),
                templatePromiseArr;
                //grab partials first
                templatePromiseArr = this._getPartials(partials);
                //grab the main template, push the promise to the end of the promise array
                templatePromiseArr.push(this._getSingleTemplate(templateName, true));
                $.when.apply(this, templatePromiseArr).done(function() {
                    //when all promises have returned...
                    //grab the last one... it's the main template
                    var mainTemplateArg = arguments[arguments.length-1];
                    templateFullyLoaded.resolve(mainTemplateArg[0], mainTemplateArg[1], mainTemplateArg[2]);
                });
                return templateFullyLoaded.promise();
            }
        }
    };
    return _templateLoader;
});