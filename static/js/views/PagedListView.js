// pagedListView
define([
    'backbone',
    'underscore',
    'suiteio',
    'models/PagingCollection',
    'helpers/LazyLoaderJson'
], 
function(
    Backbone,
    _,
    suiteio,
    PagingCollection,
    LazyLoaderJson
) {
    'use strict';
    return Backbone.View.extend({
        events: function() {
            return _.extend({
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function(options) {
            var self = this;
            options = options || {};
            // render items to this hb template
            this.templateName = options.templateName;
            this.url = options.url;
            this.listName = options.name;
            this.activeNamedFilter = options.namedFilter || '';
            this.startPage = options.start || 1;
            this.skipFirst = options.skipFirst || 0;
            this.loadFirstPage = options.firstPage || false;
            this.setElement(options.el);
            this.pageSize = options.pageSize || 15;
            this.threshold = options.threshold || 130;
            this.filterContainer = options.filterContainer || '';

            // scrollwatch element
            this.scrollerEl = options.scrollerEl || $(window);
            this.$list = this.$('.paginatedList');
            this.$('.namedFilter').on('click', function(e) { self.toggleNamedFilter(e) });
            this.$('.ctxtSearchInput').on('keyup', function(e) { self.filterKeyup(e) });

            var startingUrl = (this.activeNamedFilter) ? (this.url + '?filter=' + this.activeNamedFilter) : this.url;  
            // define the collection
            this.collection = new PagingCollection.collection([], {
                urlRoot: self.url,
                startPage: this.startPage,
                skipFirst: this.skipFirst,
                pageSize: this.pageSize,
                bottomed: false,
                tastypie: false
            });   
            this.collection.fetch({context:self.collection}).done(function() {
                if(!this.length) {
                    self.trigger('noListViewResults');
                } else {
                    self.trigger('listViewReady');
                }
            }).error(function() {
                self.trigger('errorFetchingCollection');
            });
        },

        toggleNamedFilter: function(e) {
            var $cTarget = $(e.currentTarget);
            var filter = $cTarget.data('filter');
            if(filter==this.activeNamedFilter) {
                return;
            }
                // this.activeNamedFilter = null;
                // $cTarget.removeClass('active');
            this.activeNamedFilter = filter;
            $cTarget.addClass('active');
            $cTarget.siblings().removeClass('active');
            this.filterThis(e);
        },

        filterKeyup: function(e) {
            var self = this;
            var code = e.charCode || e.keyCode || e.which;
            var timeout = 700;
            if (self.filterDoneTyping) {
                clearTimeout(self.filterDoneTyping);
            }
            if(code === 27) { return; }
            if(code <= 20 || code >=90) { return; }

            self.filterDoneTyping = setTimeout(function() { 
                self.filterThis(e);
            }, timeout);

        },

        filterThis: function(e) {
            var self = this;            
            var filteredUrl = (this.activeNamedFilter) ? (this.url + '?filter=' + this.activeNamedFilter) : this.url;  
            var connector = '?q=';
            var q = this.$('.ctxtSearchInput').val();
            if(q) {
                if(q==this.currentQuery) { return; }
                if(q && q.length) {
                    // q = q.toLowerCase().replace(/\s\s+/g, ' ').replace(/[^a-z\d\s]+/gi, "").trim().replace(/\s/ig, '-');    
                    if(this.activeNamedFilter) {
                        connector = '&q=';
                    }
                    filteredUrl = filteredUrl + connector + q
                }
            }
            
            this.currentQuery = q;
            this.loadFirstPage = true;
            this.startPage = 0;

            var listContainer = this.$('.paginatedList');
            listContainer.html('');                

            this.collection.urlRoot = filteredUrl
            this.collection.allReset();

            this.collection.fetch({context:self.collection}).done(function() {
                if(!this.length) {
                    self.trigger('noListViewResults');
                } else {
                    self.trigger('listViewFiltered', self.activeNamedFilter);
                }
            }).error(function(e) {
                self.trigger('errorFetchingCollection');
            });


        },

        fetch: function() {
            var self = this;
            this.startLazyLoader = false;
            if(this.loadFirstPage) {
                var items = self.collection.getJSONAtPage(0);
                if(items) {
                    self.renderItems(items, true);    
                    if(items.length>=this.pageSize) {
                        self.setupLazyLoader(); 
                    }                    
                } else {
                    self.trigger('noListViewResults');
                }
            } else {
                self.setupLazyLoader();
            }
        },

        setupLazyLoader: function() {
            var self = this;
            this.lazyLoader = new LazyLoaderJson({
                threshold: self.threshold,
                scrollWatch: self.scrollerEl,
                contentContainer: self.$list,
                id: this.cid + self.listName,
                collection: self.collection,
                render: function(items) {
                    if(items.bottomed) {
                        return;
                    }
                    self.renderItems(items.objects);
                },
                renderContext: this
            });
            this.lazyLoader && this.lazyLoader.kickOff();           
        },

        renderItems: function(items, firstpage) {
            this.template = suiteio.templateLoader.getTemplate(this.templateName);
            firstpage = firstpage || false;
            var self = this;
            var $domFrag = $(document.createDocumentFragment());
            this.template.done(function(tmpl) {
                _(items).each(function(item) {
                    $domFrag.append(tmpl(item));
                });
                if(firstpage) {
                    self.$list.html($domFrag);    
                } else {
                    self.$list.append($domFrag);
                }
            });
        },

        onCollectionResetSync: function(collection) {
            this.$list.empty();
            this.renderFirstPage();
            this.setupLazyLoader(collection);
        },

        destroy: function() {
            this.$('.namedFilter').off();
            this.$('.ctxtSearchInput').off();            
            this.lazyLoader && this.lazyLoader.destroy();
            this.stopListening();
        }
    });
    return PagedListView;
});