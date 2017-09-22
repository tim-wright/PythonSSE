define([
        'jquery',
        'qlik',
        './properties',
        './initialproperties',
        './lib/js/extensionUtils',
        'text!./lib/css/scoped-bootstrap.css',
        'text!./lib/partials/template.html',
],
function ($, qlik, props, initProps, extensionUtils, cssContent, template) {
    'use strict';

    extensionUtils.addStyleToHeader(cssContent);

    console.log('Initializing - remove me');

    return {

        definition: props,

        initialProperties: initProps,

        snapshot: { canTakeSnapshot: true },

        // Angular Support (uncomment to use)
        template: template,

        // Angular Controller
        controller: ['$scope', function ($scope) {
            $scope.variableValue = '';

            var app = qlik.currApp(this);
            app.variable.getContent($scope.layout.props.variableName,function ( reply ) {
                console.log('r',reply);
                if($scope.layout.props.variableType == 'number'){
                    $scope.variableValue = parseFloat(reply.qContent.qString);
                }
                else{
                    $scope.variableValue = reply.qContent.qString;   
                }
            } );
           
            $scope.charInput = function(e){
                //console.log('press',e);
                var code = (e.keyCode ? e.keyCode : e.which);
                if(code == 13) { //Enter keycode
                    $scope.changeVar();
                }
            };

            $scope.changeVar = function(){
                //alert($('#input-'+$scope.layout.props.variableName).val());
                var d = $scope.layout.props.disabled+'';
                if(!$scope.layout.props.disabled){
                    console.log('mod var', $scope.layout.props.variableName+' = '+$scope.variableValue)
                    app.variable.setContent($scope.layout.props.variableName,$scope.variableValue);  
                }
                else {
                    console.log('mod var disabled', $scope.layout.props.variableName)
                }
            };
        }]
    };

});
