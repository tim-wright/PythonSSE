define( [], function () {
	'use strict';

	
	var variableName = {
		ref: "props.variableName",
		label: "Varible Name",
		type: "string",
		expression: "optional",
		show: true
	};

	var variableType = {
		ref: "props.variableType",
		label: "Variable Type",
		type: "string",
		show: true,
		component: 'dropdown',
		defaultValue: 'text',
		options: [
			{
				value: "text",
				label: "Text"
			}, 
			{
				value: "number",
				label: "Number"
			}
		]
	};

	// variable Panel
	var variablePanel = {
		label: "Variable",
		items: {
			variable: {
				type: "items",
				items: {
					variableName: variableName,
					variableType: variableType
				}
			}
		}
	};

	// Appearance Panel

	var variableTitle = {
		ref: "props.variableTitle",
		label: "Varible Title",
		type: "string",
		expression: "optional",
		show: true
	};

	var variableDesc = {
		ref: "props.variableDesc",
		label: "Varible help text",
		type: "string",
		expression: "optional",
		show: true
	};

	var preText = {
		ref: "props.preText",
		label: "Text to add before input",
		type: "string",
		expression: "optional",
		show: true
	};

	var postText = {
		ref: "props.postText",
		label: "Text to add after input",
		type: "string",
		expression: "optional",
		show: true
	};

	var inputDisabled = {
		ref: "props.disabled",
		label: "Disable Input",
		type: "string",
		expression: "optional",
		show: true
	};

	var appearancePanel = {
		label: "Settings",
		items: {
			uses:"settings",
			settings: {
				type: "items",
				label: "Settings",
				items: {
					variableTitle: variableTitle,
					variableDesc: variableDesc,
					preText: preText,
					postText: postText,
					inputDisabled: inputDisabled
				}
			}
		}
	};

	// Return values
	return {
		type: "items",
		component: "accordion",
		items: {
			variablePanel: variablePanel,
			appearance: appearancePanel
		}
	};

} );
