// AdminMonitorView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'dropzone',
    'views/ModerateView',
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Dropzone,
    ModerateView,
    PagedListView
) {
    'use strict';
    var AdminMonitorView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .providerEdit': 'launchProviderEditor'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },
        initialize: function(options) {
            if(!suiteio.loggedInUser && !suiteio.loggedInUser.get('isModerator')) { return; }
            var self = this;
            options = options || {};
            this.options = options;
            this.adminType = options.adminType || '';
            
            this.rootUrl = '/admin/' + this.adminType;
            if(!this.adminType || this.adminType == 'home') {
                this.rootUrl = '/admin';
            } 
            
            this.moderator = suiteio.loggedInUser.toJSON();
            console.log('root url is ' + this.rootUrl);

            var $el = $('#admin-' + this.adminType);            
            console.log('admintype is ' + this.adminType);
            this.templatePromise = suiteio.templateLoader.getTemplate('admin-monitor');
            this.providerEditTmplPromise = suiteio.templateLoader.getTemplate('link-provider-editor');

            if($el.length) {
                console.log('straight to afterRender()');
                this.setElement($el);
                this.afterRender();
            } 
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'GET',
                data: {
                    spa: true,
                    viewtype: self.adminType
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;

            this.fetchContext().then(function(context) {
                self.templatePromise.done(function(tmpl) {
                    if(self.adminType == 'login') {
                        var ctxt = context;
                        context = $.extend(ctxt, {csrf: suiteio.csrf});
                    }
                    $html = $(tmpl(context));
                    // self.$el.html($html);
                    if($html.length > 1) {
                        $el = $('<div/>').append($html);
                    } else {
                        $el = $html.eq(0);
                    }
                    if(self.$el.is(':empty')) {
                        //first time render
                        self.setElement($el);
                    } else {
                        self.$el.html($html.html());
                    }
                    self.trigger('renderComplete', self.$el, self.rootUrl);
                });      
            });
        },

        afterRender: function() {
            var self = this;
            console.log('viewtype is ' + this.adminType);
            if(this.adminType) {
                switch(this.adminType) {
                    case 'tags':
                        console.log('set up tags please');
                    break;    
                    default:
                        this.startMonitorPaginator();
                    break;                                    
                }
            }
            this.clearAllMainViews(['moderateView']);
            this.moderateView = new ModerateView({
                moderator: self.moderator
            });            
        },

        startMonitorPaginator: function() {
            var self = this;
            var url = this.rootUrl;
            var $listViewEl = this.$('.monitorListView');
            var namedFilter = this.namedFilter || '';
            // var $filterContainer = this.$('.storyListFilter');
            var template;
            switch(this.adminType) {
                case 'stories':
                    template = 'story-teaser';
                break;
                case 'suites':
                    template = 'suite-teaser';
                break;                
                case 'members':
                    template = 'admin-user-teaser';
                break;                                
                case 'links':
                    template = 'link-item';
                break;                  
                case 'flags':
                    template = 'flag-teaser';
                break;                  
            }
            this.moderationListView && this.moderationListView.destroy();
            this.moderationListView = new PagedListView({
                el: $listViewEl,
                firstPage: true,
                url: url,
                templateName: template,
                namedFilter: namedFilter,
                // filterContainer: $filterContainer,
                name: 'monitorpaged'
            });
            self.listenToOnce(self.moderationListView, 'listViewReady', function() {
                self.moderationListView.fetch();
            });
            this.listenTo(self.moderationListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                console.log('hey cool; listviewfiltered...');
                // if(namedFilter=='suite') {
                //     this.moderationListView.templateName = 'suite-teaser';
                // } else if(namedFilter=='user') {
                //     this.moderationListView.templateName = 'user-teaser';
                // }
                self.moderationListView.fetch();
            });               
            self.listenTo(self.moderationListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                var memberName = suiteio.loggedInUser.get('firstName') || suiteio.loggedInUser.get('fullName') || 'you who cannot be named';
                $listViewEl.find('.paginatedList').html('<div class="centered no-notifs noNotifs">Nothing in this list!');
            });
        },

        setupProviderImageUpload: function() {
            console.log('setting up provider img upload');
            var self = this;
            var url = '/l/api/upload_provider_image';
            if(this.providerImgDropzone) {
                this.providerImgDropzone.destroy();
            }
            this.providerImgDropzone = new Dropzone('.uploadProviderImage', { url: url, paramName: "image", updateprovider: true });
            this.providerImgDropzone.on("sending", function(file, xhr, formData) {
                formData.append("csrfmiddlewaretoken", suiteio.csrf);
            });
            this.providerImgDropzone.on("success", function(data) {
                var response = JSON.parse(data.xhr.response);
                console.log(response);
                console.log(response.pk);
                var attrs = {}
                $('.tempImageUpload').empty();
                $('.uploadProviderImage').html('');
                $('.providerEditForm .providerImage').css('background-image', 'url("'+response.image_url+'")').data('pk', response.pk);
                console.log('says here we\'re done!');
            });
            $('.uploadProviderImage').click(); // Go!
        },

        launchProviderEditor: function(e) {
            var self = this;
            console.log('fire provider editor!');
            var $target = $(e.currentTarget);
            var providerId = $target.data('id');

            var actionDecision = {};
            actionDecision.title = 'Edit this external link provider';
            actionDecision.mainContent = self.providerEditor;

            actionDecision.act1 = { action: 'done', text: 'Done', persist: true};
           
            this.listenTo(suiteio.vent, 'uploadProviderIcon', function() {
                self.setupProviderImageUpload();
            });           

            this.listenToOnce(suiteio.vent, 'genericModalClosed', function() {
                self.stopListening(suiteio.vent);
            });

            this.listenToOnce(suiteio.vent, 'done', function(e) {
                console.log('saving...');
                console.log($(e.currentTarget));
                var $form = $('.providerEditForm');
                var url = self.rootUrl;
                var providerName = $form.find('.providerName').val();
                var providerUrl = $form.find('.providerUrl').val();
                var providerImagePk = $form.find('.providerImage').data('pk') || '';
                suiteio.vent.trigger('okToClose');

                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {
                        updateprovider: true,
                        providerid: providerId,
                        providerimg: providerImagePk,
                        name: providerName,
                        url: providerUrl
                    },
                    success: function() {
                        self.afterRender();
                    }
                });
            });                
            suiteio.genericActionModal(actionDecision);
            this.fetchLinkProviderAttrs(providerId).then(function(context) {

                self.providerEditTmplPromise.done(function(tmpl){                 
                    var $providerEditor = $(tmpl(context));
                    var wait = setTimeout(function() { 
                        $('.genericModalBodyContent').html($providerEditor);
                    }, 1000);
                });    

            });       
        },

        fetchLinkProviderAttrs: function(providerId) {
            var self = this;
            return $.ajax({
                url: '/api/v1/link_provider/' + providerId,
                type: 'GET'
            });
        },
        
        modQuickApprove: function(e) {
            if(!suiteio.loggedInUser) { return; }
            var self = this,
                $target = $(e.currentTarget),
                $userId = $target.data('id'),
                url = '/admin/api/quick_approve'

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    userid: $userId
                },
                success: function() {
                    suiteio.notify.alert({msg: 'Approved!'});
                    self.showModStories();
                }
            });
        },

        modDel: function(e) {
            if(!suiteio.loggedInUser) { return; }
            var self = this,
                $target = $(e.currentTarget),
                $userId = $target.data('id');
            suiteio.notify.prompt({
                msg: 'Are you sure you want delete this member?'
            }).done(function(decision) {
                if(decision) {
                    var url = '/admin/api/delete_spam';
                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: {
                            userid: $userId
                        },
                        success: function() {
                            suiteio.notify.alert({msg: 'Deleted!'});
                            self.showModStories();
                        }
                    });
                }
            });
        },

        clearFlag: function(e) {
            console.log('trying to clear a flag');
            var self = this,
                $parent = $(e.currentTarget).closest('.drawerModFlag'),
                thisId = $parent.data('id');
            $.ajax({
                url: '/admin/api/clear_flag',
                type: 'POST',
                data: {
                    flagid: thisId
                },
                success: function() {
                    $parent.remove();
                    self.fetchModTopLevelStats();
                }
            });
        },

        toggleApproved: function(e) {
            this.moderateView.toggleApproved(e);
        },

        toggleFeatured: function(e) {
            this.moderateView.toggleFeatured(e);
        },

        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },
        
        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },

        respondTo: function(e) {
            suiteio.respondTo(e);
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },        

        clearAllMainViews: function() {
            var views = ['moderateView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },

        destroy: function() {
            this.clearAllMainViews();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });

    return AdminMonitorView;
});