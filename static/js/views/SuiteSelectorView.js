// SuiteSelectorView.js
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView
    ) {
    'use strict';
    var SuiteSelectorView = Backbone.View.extend({
        events: function() {
            return _.extend({

                'click .suiteSelector': 'selectSuite',
                'hide.bs.modal': 'exit'

            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            this.suiteSelectorTmplPromise = suiteio.templateLoader.getTemplate('suite-selector-modal', ['suite-selectable']); 

            this.options = options || '';
            console.log(options);
            this.contentType = options.contentType || 'story';
            this.contentId = options.contentId || '';

            this.contentTitle = options.contentTitle;
            this.contentResourceUri = options.contentResourceUri;
            this.create = this.options.create || false;
            this.suitesToAdd = [];
            this.suitesToRemove = [];
            this.rootUrl = '/s/api/suite_selector';
        },


        fetchContext: function() {
            var self = this;
            var url = this.rootUrl;
            var contentId = self.contentId;
            var contentType = self.contentType;

            console.log(contentId + ', ' + contentType);

            var $tempAddList = '';
            if(this.suitesToAdd) {
                $tempAddList = this.suitesToAdd.toString();
            }
            return $.ajax({
                url: url,
                type: 'POST',
                data: {
                    contentid: contentId,
                    contenttype: contentType,
                    create: self.create
                }
            });
        },

        openSelector: function() {  
            var self = this;
            var $storyId = self.contentId || '';

            this.fetchContext().then(function(context) {
                self.suiteSelectorTmplPromise.done(function(tmpl) {
                    self.selectorModal = $(tmpl(context));
                    self.selectorModal.modal(); 
                    self.setElement(self.selectorModal);

                    // var $suiteSelectorContainer = $('.suiteSelectorList'),
                    //     $newSuiteCta = '<div class="suite-teaser suite-selector selectorNewSuite new-cta"><div class="suite-teaser-main"><div class="suite-cta-content centered"><div class="butt"><i class="io io-ios-browsers-outline"></i> Create a new Suite</div></div></div></div></div>';                  

                    var $tempAddList = self.suitesToAdd;
                    self.loadSuitesList();

                    self.listenTo(suiteio.vent, 'newSuite', function(suiteId) {
                        // self.suitesToAdd.push(suiteId);
                        self.doAddRemove(suiteId).then(function() {
                            self.loadSuitesList();
                        });
                    });
                    $('.suiteSelectorList').velocity('stop', true).velocity({ marginTop: 240 }, {
                      duration: 240,
                      delay: 200
                    });
                });
            });

        },

        closeModal: function() {
            this.selectorModal.modal('hide');
        },

        loadSuitesList: function(e) {
            var self = this;
            var $listEl = this.$('.suiteSelectorList');


            // var url = '/s/api/suite_selector';
            var url = this.rootUrl + '?type=' + this.contentType + '&cid=' + this.contentId;
            if(self.selectorListView) {
                self.selectorListView && self.selectorListView.destroy();
            }
            self.selectorListView = new PagedListView({
                    firstPage: true,
                    scrollerEl: $('.modalScollable'),
                    el: $listEl,
                    url: url,
                    templateName: 'suite-selectable',
                    name: 'mysuiteselectorlist'
            });
            self.listenTo(self.selectorListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                self.selectorListView.fetch();
            });                     
            self.listenToOnce(self.selectorListView, 'listViewReady', function() {
                self.selectorListView.fetch();
                $('.suiteSelectorList').velocity('transition.fadeIn', 220);
            });
            self.listenToOnce(self.selectorListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                $listEl.find('.paginatedList').html('');
            });


            // var url = this.rootUrl + '?type=' + this.contentType + '&cid=' + this.contentId;
            // var $listViewEl = $('.suiteSelector');
            
            //     if(self.selectorListView) {
            //         self.selectorListView && self.selectorListView.destroy();
            //     }
            //     self.selectorListView = new PagedListView({
            //             firstPage: true,
            //             scrollerEl: $('.modalScrollable'),
            //             el: $listViewEl,
            //             url: url,
            //             templateName: 'suite-selectable',
            //             name: 'selectorsuites'
            //     });
            //     self.listenTo(self.selectorListView, 'listViewFiltered', function(namedFilter) {
            //         namedFilter = namedFilter || '';
            //         self.selectorListView.fetch();
            //     });                     
            //     self.listenToOnce(self.selectorListView, 'listViewReady', function() {
            //         console.log('ready!');
            //         self.selectorListView.fetch();
            //     });
            //     self.listenToOnce(self.selectorListView, 'errorFetchingCollection' || 'noListViewResults', function() {
            //         console.log('No results');
            //     });

        },

        doAddRemove: function(suiteId) {
            var self = this;
            if(this.create) {
                suiteio.notify.alert({
                    type: 'losenge',
                    delay: 4000,
                    msg: 'Added!'
                 });
                return;
            }

            var tempAddList = this.suitesToAdd;
            var tempRemoveList = this.suitesToRemove;
            var $addSuites = [];
            var $removeSuites = [];

            return $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    toggle: true,
                    suiteid: suiteId,
                    contentid: self.contentId,
                    contenttype: self.contentType
                }
            });                

            // // Clean up add + remove lists
            // for(var i=0, l=tempAddList.length, item ; i<l ; ++i) {
            //     item = parseInt(tempAddList[i], 10);
            //     $addSuites.push(item);
            // }

            // for(var i=0, l=tempRemoveList.length, item ; i<l ; ++i) {
            //     item = parseInt(tempRemoveList[i], 10);
            //     $removeSuites.push(item);
            // }

            // $.ajax({
            //     url: url,
            //     type: 'POST',
            //     data: {
            //         addtype: self.contentType,
            //         pk: self.contentId,
            //         create: this.create,
            //         addsuites: JSON.stringify($addSuites),
            //         removesuites: JSON.stringify($removeSuites)
            //     },
            //     success: function(response) {
            //         var msg = '', conjunction = '', removed_string = '', added_string = '';
            //         var suites = response.added;

            //         if(response.added) {
            //             for(var i=0, l=response.added.length, title ; i<l ; ++i) {
            //                 var prefix = ', ';
            //                 if(i == 0) { msg = 'Added to '; prefix = ''; } else if(!response.added[i+1]) { prefix = ' and '; }
            //                 var string = prefix + '<strong>' + response.added[i] + '</strong>';
            //                 added_string += string
            //             }
            //         }

            //         if(response.removed) {
            //             for(var i=0, l=response.removed.length, title ; i<l ; ++i) {
            //                 var prefix = ', ';
            //                 if(i == 0) { prefix = ''; } else if(!response.removed[i+1]) { prefix = ' and '; }
            //                 removed_string += prefix + response.removed[i];
            //             }
            //         }

            //         if(added_string && removed_string) { conjunction = ' and removed from '} else if(!added_string && removed_string) { conjunction = 'Removed from '}
            //         msg += added_string + conjunction + removed_string;
                    
            //         suiteio.notify.alert({
            //             delay: 4000,
            //             type: 'losenge',
            //             msg: msg
            //          });
            //         suiteio.vent.trigger('storySuitesUpdated', self.contentId, suites);             
                    

            //     }
            // });            
        },        

        selectSuite: function(e, starterSuite) {
            var self = this;
            var $target = $(e.currentTarget);
            var $statusBlob = $target.find('.selectorStatus');
            var suiteId;

            if(starterSuite) {
                suiteId = starterSuite;
            } else {
                suiteId = $target.data('suite'); // (suite Id)
            }       

            var addIt = true;
            if($target.hasClass('active')) {
                addIt = false;
            }
            if(addIt) {
                $statusBlob.velocity('stop', true).velocity('transition.expandIn', 100);
                this.doAddRemove(suiteId).then(function(status) {
                    if(status) {
                        $statusBlob.addClass('done');
                        suiteio.vent.trigger('storySuitesUpdated', self.contentId, self.contentType, suiteId);             
                       var wait1 = setTimeout(function() { 
                            $statusBlob.velocity('stop', true).velocity('reverse');
                            $target.addClass('active');
                        }, 300);        
                       var wait2 = setTimeout(function() { 
                           $statusBlob.removeClass('done');
                        }, 300 + 100);                                          
                    }
                });        
            } else {
                this.doAddRemove(suiteId);
                $target.removeClass('active');
            }

        },

        createNewSuite: function() {
            suiteio.createSuiteModal(true);
        },

        exit: function(e) {
            this.trigger('closeSuiteSelectorView');
            this.$el.modal('hide');
            this.$el.remove();
        },

        destroy: function() {
            this.stopListening(suiteio.vent);
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.$el.remove();
        },

    });
    return SuiteSelectorView;
});