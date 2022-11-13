// AdminStatsView
define([
    'jquery',
    'suiteio',
    'backbone',
    'underscore',
    'lib/highstock',
    'views/PagedListView',
    'moment'
],
function(
    $,
    suiteio,
    Backbone,
    _,
    Highcharts,
    PagedListView,
    moment
) {
    'use strict';
    var AdminStatsView = Backbone.View.extend({       
        events: function() {
            return _.extend({
                // 'click .accrualEntry': 'toggleAccrualDetails',
                'click .rangeSelector li': 'updateRange',
                'click .resetZoom': 'resetZoom',
                'click .statsTab': function(e) {
                   this.onStatsSectionChange(e);
                },                
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function () {
            var self = this;
            // this.$el = $('.notifsContainer');
            // this.setElement($('.notifsContainer'));
            this.statsTmplPromise = suiteio.templateLoader.getTemplate('admin-stats-shell');
            this.render();

            // this.chartData = new Backbone.Model();

            this.width = 32;

            this.statsSummaryTmpl = suiteio.templateLoader.getTemplate('stats-summary');
            this.storyMiniTeaserTmpl = suiteio.templateLoader.getTemplate('stats-mini-story');

            this.userTeaserTmpl = suiteio.templateLoader.getTemplate('user-teaser');

            this.showstories = true;
            this.showpageviews = true;
            
            this.currentTarget = 'users';
            this.timePeriod = 30 // default period
            this.url = '/admin/stats';


            var $el = $('#admin-stats-view');
            // $el.find('.tip').tooltip('destroy').tooltip();
            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete');
            } else {
                this.render();
            }
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            self.statsTmplPromise.done(function(tmpl) {
                $html = $(tmpl({
                }));
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
                // self.trigger('renderComplete', self.$el);
        
            });      
            self.fetchFreshData().then(function(data) {
                self.chartData = new Backbone.Model(data.chartdata);
                self.renderStatsSummary(data.summary);
                self.trigger('renderComplete', self.$el);
            });
        },

        loadChart: function() {
            var self = this;

            self.highchartIt();    
            self.$('.royDetail').tooltip();

            // (function (H) {
            //     H.wrap(H.Tooltip.prototype, 'hide', function () {});
            // }(Highcharts));

            self.listenTo(self.chartData, 'change', function() {
                self.updateChartSeries(self.currentTarget);
            });
        },

        fetchFreshData: function() {
            var $target = this.currentTarget;
            var $period = this.timePeriod;
            var self = this;
            var url = self.url;
           
            var freshData = $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    timeperiod: $period,
                    target: $target
                },
            });
            return freshData;
        },

        centerOfScreen: function() {
            var width = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
            return width/2;
        },

        togglePaymentList: function() {
            $('.paymentsList').toggle();
        },

        loadTopStories: function() {
            console.log('loading global top stories');
            var self = this;
            var $listViewEl = self.$('.globalTopStoriesList');
            var $url = self.url + '?type=topstories&timeperiod=' + this.timePeriod;
           
            self.statsTopStoriesListView && self.statsTopStoriesListView.destroy();
            self.statsTopStoriesListView = new PagedListView({
                el: $listViewEl,
                url: $url,
                templateName: 'story-stats-teaser',
                name: 'global-stats-topstories'
            });
            self.listenToOnce(self.statsTopStoriesListView, 'listViewReady', function() {
                self.statsTopStoriesListView.fetch();
            });
            self.listenToOnce(self.statsTopStoriesListView, 'noListViewResults', function() {
                self.$('.globalTopStoriesList .paginatedList').html('<div class="no-notifs noNotifs">No top stories to report yet...');
            });
        },

        showMoreAccrualData: function(e) {
            var self = this;
            var $ctarget = $(e.currentTarget);
            var isToday = $ctarget.data('today') || false;
            if(isToday) {

            }
            $ctarget.toggleClass('open');
            this.$('.accrualEgg').not($ctarget).removeClass('open');
        },

        clearData: function() {
            this.chartData.clear();
            var chart = this.chart;
            var seriesLength = chart.series.length;
            for(var i = seriesLength -1; i > -1; i--) {
                chart.series[i].remove();
            }
        },

        updateRange: function(e) {
            var self = this;
            var $ctarget = $(e.currentTarget);
            $('.myStatsRangeSelector').text($ctarget.text());
            $('.myStatsRange .dateChange li').removeClass('active');
            $ctarget.parent('li').addClass('active');

            this.timePeriod = $ctarget.data('time-period');
            
            this.chart.showLoading();
            self.clearData();  
            this.fetchFreshData().then(function(data) {
                self.chart.hideLoading();
                self.chartData.set(data.chartdata);
                self.renderStatsSummary(data.summary);
            });
        },

        renderStatsSummary: function(data) {
            console.log('rendering stats summary');
            data = data || { placeholder: true };
            var self = this;
            var $html;
            var currentTarget = this.currentTarget;
            this.statsSummaryTmpl.done(function(tmpl) {
                $html = $(tmpl(data));
                self.$('.statsSummary').html($html);
            });
            if(self.currentTarget=="globalreads") {
                self.loadTopStories();
            }            
        },

        onStatsSectionChange: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            this.currentTarget = $target.data('target').replace('#', '');

            self.chart.showLoading();
            self.clearData();            
            this.fetchFreshData().then(function(data) {
                self.chartData.set(data.chartdata);
                self.chart.hideLoading();
                self.renderStatsSummary(data.summary);
            });
        },
           
        updateChartSeries: function(target) {
            var self = this;
            var yAxis;
            var chartSeries;
            this.chart.hideLoading();
            console.log('target = ' + target);
            
            if(target === 'users') {
                chartSeries = ['allusers', 'activeusers', 'activeratio']
            }
            
            if(target === 'globalposts') {
                chartSeries = ['allnew', 'newapproved', 'responses', 'extresponses']
            }

            if(target === 'globalreads') {
                chartSeries = ['reads', 'pageviews']
            }

            if(chartSeries && chartSeries.length) {
                for(var i=0, l=chartSeries.length, item ; i<l ; ++i) {
                    self.chart.addSeries(getSeries(self.chartData.get(chartSeries[i]), getSeriesOptions(chartSeries[i])));
                }
            }

        },

        resetZoom: function() {
            this.chart.zoomOut();
            this.$('.resetZoom').hide();
        },

        setZoom: function() {
            this.$('.resetZoom').show();
        },

        processArticleData: function(articles) {
            var processedArticles = {},
                //articlesPerDayChartData = [],
                utcDate = '',
                value = '';
            if(!articles) {
                return null;
            }
            for(var key in articles) {
                utcDate = Date.parse(key + ' UTC');
                value = articles[key];
                processedArticles[utcDate] = value;
                //articlesPerDayChartData.push([utcDate, value]);
            }
            return processedArticles;
        },

        highchartIt: function() {
            console.log('trying to render the chart');
            var self = this;
            var series = [];
                 series.push(
                    getSeries(this.chartData.get('allusers'), getSeriesOptions('allusers')),
                    getSeries(this.chartData.get('activeusers'), getSeriesOptions('activeusers')),
                    getSeries(this.chartData.get('activeratio'), getSeriesOptions('activeratio'))
                );

            this.chart = Highcharts.StockChart({
                credits: { enabled: false },
                events: {
                    load: function(event) {
                        //When is chart ready?
                        // self.fetchFreshData();
                    }
                },                       
                chart: {
                    zoomType: 'x',
                    resetZoomButton: {
                        theme: {
                            display: 'none'
                        }
                    },                    
                    renderTo: self.$('.userStatsPlot').get(0),
                    plotBorderColor: '#fff',
                    backgroundColor: '#fff',
                    plotBackgroundColor: '#fff',
                    spacingLeft: 0,
                    spacingRight: 0,
                    spacingTop: 0,
                    spacingBottom: 0,
                    ignoreHiddenSeries: true
                },
                rangeSelector : {
                    enabled: false
                },
                scrollbar : {
                    enabled : false
                },
                navigator : {
                    enabled : false
                },
                navigation: {
                    buttonOptions: {
                        enabled: false
                    }
                },
                title: {
                    text: null
                },
                plotOptions: {
                    column: {
                        stacking: 'normal'
                    }
                },
                tooltip: {
                    backgroundColor: 'transparent',
                    borderColor: '#ccc',
                    borderRadius: 0,
                    borderWidth: 0,
                    useHTML: true,
                    snap: false,
                    shadow: false,
                    zIndex: 1000,
                    followPointer:true,
                    style: { fontFamily: '\'proxima-nova\'' },
                    positioner: function (labelWidth, labelHeight, point) {
                        var tooltipX, tooltipY;
                        if (point.plotX + labelWidth > this.chart.plotWidth) {
                            tooltipX = point.plotX + this.chart.plotLeft - labelWidth - 1;
                        } else {
                            tooltipX = point.plotX + this.chart.plotLeft + 1;
                        }
                        tooltipY = this.chart.plotTop + 100;
                        return {
                            x: tooltipX,
                            y: tooltipY
                        };
                    },
                    formatter: function() {
                        var tooltip = '',
                            date,
                            reads = 0,
                            allusers = 0,
                            activeusers = 0,
                            activeratio = 0,
                            pviews = 0,
                            roys = 0.0,
                            readRate;
                        _(this.points).each(function(point) {
                            date = moment(point.x).format('ddd, MMM Do, YYYY');
                            switch(point.series.options.id) {
                                case 'reads-series':
                                    reads = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + point.y + '</div><div class="statLegendLabel">Reads</div></div>';
                                    break;
                                case 'pageviews-series':
                                    pviews = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + point.y + '</div><div class="statLegendLabel">Views</div></div>';
                                                     readRate = ~~(10000*(reads / pviews)) / 100;
                                        tooltip += '<div class="tipBlock read-rate"><div class="statNumber percentage">' + readRate + '%</div><div class="statLegendLabel">Read rate</div></div>';
                                    break;
                                case 'allusers-series':
                                    allusers = point.y;
                                    break;
                                case 'activeusers-series':
                                    activeusers = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + activeusers + '</div><div class="statLegendLabel">Active users</div></div>';
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + allusers + '</div><div class="statLegendLabel">All users</div></div>';
                                    activeratio = ~~(10000*((activeusers / allusers))) / 100;
                                    tooltip += '<div class="tipBlock read-rate"><div class="statNumber percentage">' + activeratio + '%</div><div class="statLegendLabel">Active %</div></div>';
                                    break;                                    
                                case 'payments-series':
                                    // pviews = point.y;
                                    tooltip += '<p>Paid today: <strong>' + 0 + '</strong></p>';
                                    break;
                                case 'newposts-series':
                                    return false ;
                                    // pviews = point.y;
                                    tooltip += '<p>New posts: <strong>' + 0 + '</strong></p>';
                                    break;
                            }
                        });
                        tooltip = '<p class="date">' + date + '</p>' + tooltip;
                        return tooltip;
                    }
                },
                yAxis: [
                {
                    // ##### yAxis 0
                    allowDecimals: false,
                    labels: {
                        style: {color: '#999'},
                        enabled: false
                    },
                    title: {
                        text: null
                    },
                    gridLineWidth: 0,
                    gridLineColor: 'rgba(0,0,0,.04)',
                    minorGridLineWidth: 0,
                    min: 0.0
                },

                {
                    // ##### yAxis 1
                    allowDecimals: true,
                    gridLineWidth: 0,
                    gridLineColor: 'rgba(0,0,0,.02)',
                    minorGridLineWidth: 0,
                    labels: {
                        style: {
                            color: '#333333',
                            fontWeight: 'bold'
                        },
                        enabled: false
                    },
                    title: {
                        text: null
                    },
                    min: 0.0,
                    max: 1.0
                },
                {
                    // ##### yAxis 2
                    opposite: true,
                    allowDecimals: false,
                    gridLineWidth: 0,
                    minorGridLineWidth: 4,
                                        gridLineColor: 'rgba(0,0,0,.02)',
                    min: 0.0,
                    labels: {
                        enabled: false
                    },
                    title:{
                        text: null
                    }
                },
                {
                    opposite: true,
                    allowDecimals: false,
                    gridLineWidth: 0,
                    minorGridLineWidth: 0,
                    min: 0.0,
                    labels: {
                        enabled: false
                    },
                    title:{
                        text: null
                    }
                }],
                xAxis: {
                    events: {
                        afterSetExtremes: function(event){
                            if (this.getExtremes().dataMin < event.min)
                                self.setZoom();
                        }
                    },                    
                    type: 'datetime',
                    crosshair: {
                        width: 1,
                        color: '#e7e7e7',
                        dashStyle: 'shortdot'
                    },                 
                    labels: {
                        rotation: 0,
                        useHTML: true,                
                        style: {
                            marginTop: '-16px',
                            top: '-16px',
                            paddingTop: '0px',
                            color: '#ccc',
                        }
                    },
                    allowDecimals: false,
                    minRange: 7 * 24 * 3600 * 1000,
                    minTickInterval: 1000*60*60*24*30,
                    lineColor: '#e3e4e4',
                    lineWidth: 0,
                    minorTickLength: 0,
                    tickLength: 0,
                    title: {
                        text: null
                    }
                },
                legend: {
                    enabled: false
                },
                series: series
            });
        },

        destroy: function() {
            this.chart.destroy();            
        }


    });

    var getSeriesOptions = function(series) {
        var seriesOptions;
        switch(series) {
            case 'allusers':
                seriesOptions = {
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'allusers',
                    lineWidth: 0,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'allusers-series',
                    color: '#e7e7e7',
                    fillColor: '#f8f8f4',
                    zIndex: 1,
                    yAxis: 0                  
                }
            break;
            case 'activeusers':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'activeusers',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'activeusers-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;
            case 'activeratio':
                seriesOptions = {
                    zIndex: 3,
                    type: 'spline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'activeratio',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'activeratio-series',
                    color: '#1a8bba',
                    fillColor: '#f8f8f4',
                    zIndex: 3,
                    yAxis: 1,
                    dashStyle: 'shortdot'  
                }
            break;      
            case 'allposts':
                seriesOptions = {
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'allposts',
                    lineWidth: 0,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'allposts-series',
                    color: '#e7e7e7',
                    fillColor: '#f8f8f4',
                    zIndex: 1,
                    yAxis: 0                  
                }
            break;
            case 'approvedposts':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'approvedposts',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'approvedposts-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;   
            case 'responses':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'responses',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'responses-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;  
            case 'extresponses':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'extresponses',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'extresponses-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;                                          
            case 'reads':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'reads',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'reads-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;
            case 'pageviews':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'pageviews',
                    lineWidth: 1,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'pageviews-series',
                    color: 'rgba(0,0,0,.1)',
                    fillColor: 'rgba(0,0,0,.1)',
                    zIndex: 2,
                    yAxis: 0   
                }
            break;            
            case 'words-added':
                seriesOptions = {
                    name: 'words-added',
                    zIndex: 1,
                    type: 'column',
                    column: {
                        stacking: 'normal'
                    },
                    id: 'words-added-series',
                    color: 'rgba(26,139,186,.9)',
                    fillColor: 'rgba(26,139,186,.9)',
                    yAxis: 2
                }
            break;
            case 'words-removed':
                seriesOptions = {
                    yAxis: 2,
                    name: 'words-removed',
                    zIndex: 1,
                    type: 'column',
                    column: {
                        stacking: 'normal'
                    },
                    id: 'words-removed-series',
                    color: '#ccc',
                    fillColor: '#ccc'
                }
            break;
            case 'newposts':
                seriesOptions = {
                    yAxis: 2,
                    name: 'newposts',
                    zIndex: 1,
                    type: 'column',
                    column: {
                        stacking: 'normal'
                    },
                    id: 'newposts-series',
                    color: '#333',
                    fillColor: '#e7e7e7',
                }
            break;
            case 'suiteviews':
                seriesOptions = {
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'suiteviews',
                    lineWidth: 0,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'suiteviews-series',
                    color: '#1a8bba',
                    fillColor: '#1a8bba',
                    zIndex: 2,
                    yAxis: 0                  
                }
            break;
            case 'suitefollows':
                seriesOptions = {
                    type: 'areaspline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'suitefollows',
                    lineWidth: 0,
                    states: {
                        hover: {
                            enabled: false,
                            lineWidth: 0,
                        },
                    },
                    id: 'suitefollows-series',
                    color: '#eee',
                    fillColor: '#eee',
                    zIndex: 1,
                    yAxis: 0    
                }
            break;
            case 'profile-views':
                seriesOptions = {
                    yAxis: 2,
                    name: 'profileviews',
                    zIndex: 1,
                    type: 'column',
                    column: {
                        stacking: 'normal'
                    },
                    id: 'profileviews-series',
                    color: '#1a8bba',
                    fillColor: '#1a8bba',
                }
            break;
            case 'profile-follows':
                seriesOptions = {
                    yAxis: 2,
                    name: 'profilefollows',
                    zIndex: 1,
                    type: 'column',
                    column: {
                        stacking: 'normal'
                    },
                    id: 'profilefollows-series',
                    color: '#ccc',
                    fillColor: '#ccc',
                }
            break;
            }
        return seriesOptions           
    };

    var getSeries = function(data, options) {
        return _.extend({
            data: data
        }, options);
    };

    return AdminStatsView;
});