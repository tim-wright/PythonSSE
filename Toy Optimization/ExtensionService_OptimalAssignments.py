#! /usr/bin/env python3
import argparse
import json
import logging
import logging.config
import os
import sys
import time
from concurrent import futures

import ServerSideExtension_pb2 as SSE
import grpc

import pandas as pd
from pulp import LpProblem, LpMaximize, LpVariable, LpInteger, lpSum, value


_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class ExtensionService(SSE.ConnectorServicer):
    """
    A simple SSE-plugin created for the Column Operations example.
    """

    def __init__(self, funcdef_file):
        """
        Class initializer.
        :param funcdef_file: a function definition JSON file
        """
        self._function_definitions = funcdef_file
        if not os.path.exists('logs'):
            os.mkdir('logs')
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logger.config')
        logging.config.fileConfig(log_file)
        logging.info('Logging enabled')
        
        
        ## helper function reads in data a single time and binds it to the ExtensionService Instance (so that it doesn't have to be loaded every time function is called)
        def bind_data(self):
            data_directory = os.path.dirname(os.path.abspath(__file__))
            data_file ='preferences.csv'
            data = pd.read_csv(data_directory+'\\'+data_file, usecols=[1,2,3,4,5])

            # Create a string id of People to use in the dictionary for choices (in the LP)
            emp_id_str = [str(id) for id in data['Employee ID']]
            
            # Create a string id of Options
            options = ['Train','Plane','Bus','Boat']
            
            # Create a dictionary of  for each Person/Option category
            benefits=dict()
            for employee in emp_id_str:
                j=-1
                benefits[employee]=dict()
                for option in options:
                    j+=1
                    benefits[employee][option]=float(data[data['Employee ID']==float(employee)][option])

            # Bind the data to the instance so that it doesn't have to be reloaded on each Method (function) call
            self.benefits = benefits;
            self.options = options;
        bind_data(self)


    @property
    def function_definitions(self):
        """
        :return: json file with function definitions
        """
        return self._function_definitions

    @property
    def functions(self):
        """
        :return: Mapping of function id and implementation
        """
        return {
            0: '_optimize_assignments' 
        }

    @staticmethod
    def _optimize_assignments(self, request, context):
        """
        Determine the optimal assignment of employees to transportation given their preferences
        :param request: an iterable sequence of RowData (Employee ID, Capacity 1, Capacity 2, Capacity 3, Capacity 4)
        :return: the same iterable sequence of row data as received (best action for a single customer)
        
        Also, save a dataframe as a class attribute so that the additional columns of data can be accessed from other SSE function calls
        """
        # Iterate over bundled rows to create a SINGLE array of the request parameters
        Request_IDs=[]
        response_rows = [] # this will be used to collect results we send back to Sense
        for request_rows in request:
            # Iterating over rows in EACH bundle
            for row in request_rows.rows:
                data = [str(int(d.numData)) for d in row.duals]
                Request_IDs.append(data[0]) # The first number in the param list is the customer ID/key (distinct for each row)
            
        quant_avail = [float(quant) for quant in data[1:5]] # These are the Number of tickets from Sense Front-end

        # Initiate the LP
        prob = LpProblem("Optimal_Assignments",LpMaximize)
        # Create a dictionary of choice variables. 
        choices = LpVariable.dicts("Choice",(Request_IDs,self.options),0,1,LpInteger)
        B=self.benefits # This dictionary of benefits for all IDs was defined during __init__ above
        
        # Build up a dictionary of the available tickets for each mode of transportation
        QuantityAvailable=dict()
        i=-1
        for option in self.options:
            i+=1
            QuantityAvailable[option]=int(quant_avail[i])
        
        # Create a employee|mode level benefit dictionary - ONLY for people whose IDs were sent in the request from Qlik Sense
        benefit=dict()
        for employee in Request_IDs:
            benefit[employee]=dict()
            for option in self.options:
                benefit[employee][option]=B[employee][option]

        # Objective Function: add all the Benefit * Binary Choice variable for every employee/benefit/choice
        prob += lpSum([benefit[employee][option]*(choices[employee][option]) for employee in Request_IDs for option in self.options])

        # Constraints. One person can only be assigned a single ticket(choice constraints) - again limited to those people whose IDs were sent in the Request.
        for employee in Request_IDs:
            prob += lpSum([choices[employee][option] for option in self.options]) <=1 , ""
                
        # Additional Constraints. (total people assigned to each mode cannot exceed available number of tickets)
        for option in self.options:
            prob += lpSum([choices[employee][option] for employee in Request_IDs]) <= QuantityAvailable[option],""

        # This will solve the LP
        prob.solve()

        # Manipulate the returned/optimal choices
        data= pd.DataFrame(choices)
        
        # This will generate a col for each Customer and a row for each option. The value in each row will be 0/1, with no more than a single 1 per column.
        for column in data.columns:
            data[column] = [value(val) for val in data[column]]

        # Helper function to reshape the results from the 
        def Final_Actions(data):
            final_actions = [] 
            for col in data.columns:  
                if len(data[data[col]==1][col])==1: # if there was a binary choice for the person (they were assigned a ticket)
                    final_actions.append([int(col),data[data[col]==1][col].index[0]]) # This appends [col, row] where choice ==1, since col=employee Id and row = mode of transportation for the assigned ticket 
            return(pd.DataFrame(final_actions,columns=['Employee id','Trip Assignment'])) # Here, person is the employee ID and the Ticket assigment

        optimal_assignments = Final_Actions(data) # Call helper function from above
        employee_order = pd.DataFrame([int(float(id)) for id in Request_IDs], columns={'Employee id'}) # coerce the IDs sent from Qlik into a DataFrame
        #print(out.head())
        Qlik_ordered_assignments = employee_order.merge(optimal_assignments, how='left', left_on = 'Employee id', right_on = 'Employee id') # sorting the Optimal Assigments in the order in which the Employee IDs were received from Sense Request
        Qlik_ordered_assignments.fillna('Unassigned', inplace=True) # Fill in where there was no choice made to say "Unassigned"
        
        #for each row in the dataframe pull out the mode assigment:
        for index, row in Qlik_ordered_assignments.iterrows():
            result = row['Trip Assignment']
            # Create an iterable of Dual with a string value (since we are passing strings back to qlik)
            duals = iter([SSE.Dual(strData=result)])
            # Append the row data constructed to response_rows
            response_rows.append(SSE.Row(duals=duals))
        # Yield Row data as Bundled rows. This is what is sent back to Qlik Sense
        yield SSE.BundledRows(rows=response_rows)


    @staticmethod
    def _get_function_id(context):
        """
        Retrieve function id from header.
        :param context: context
        :return: function id
        """
        metadata = dict(context.invocation_metadata())
        header = SSE.FunctionRequestHeader()
        header.ParseFromString(metadata['qlik-functionrequestheader-bin'])
        return header.functionId

    """
    Implementation of rpc functions.
    """

    def GetCapabilities(self, request, context):
        """
        Get capabilities.
        Note that either request or context is used in the implementation of this method, but still added as
        parameters. The reason is that gRPC always sends both when making a function call and therefore we must include
        them to avoid error messages regarding too many parameters provided from the client.
        :param request: the request, not used in this method.
        :param context: the context, not used in this method.
        :return: the capabilities.
        """
        logging.info('GetCapabilities')

        # Create an instance of the Capabilities grpc message
        # Enable(or disable) script evaluation
        # Set values for pluginIdentifier and pluginVersion
        capabilities = SSE.Capabilities(allowScript=False,
                                        pluginIdentifier='NBA Optimize - Qlik',
                                        pluginVersion='v1.0.0-beta1')

        # If user defined functions supported, add the definitions to the message
        with open(self.function_definitions) as json_file:
            # Iterate over each function definition and add data to the Capabilities grpc message
            for definition in json.load(json_file)['Functions']:
                function = capabilities.functions.add()
                function.name = definition['Name']
                function.functionId = definition['Id']
                function.functionType = definition['Type']
                function.returnType = definition['ReturnType']

                # Retrieve name and type of each parameter
                for param_name, param_type in sorted(definition['Params'].items()):
                    function.params.add(name=param_name, dataType=param_type)

                logging.info('Adding to capabilities: {}({})'.format(function.name,
                                                                     [p.name for p in function.params]))

        return capabilities

    def ExecuteFunction(self, request_iterator, context):
        """
        Call corresponding function based on function id sent in header.
        :param request_iterator: an iterable sequence of RowData.
        :param context: the context.
        :return: an iterable sequence of RowData.
        """
        # Retrieve function id
        func_id = self._get_function_id(context)
        logging.info('ExecuteFunction (functionId: {})'.format(func_id))

        return getattr(self, self.functions[func_id])(self, request_iterator, context)

    """
    Implementation of the Server connecting to gRPC.
    """

    def Serve(self, port, pem_dir):
        """
        Server
        :param port: port to listen on.
        :param pem_dir: Directory including certificates
        :return: None
        """
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) ## TW : Returns a server than can service RPCs
        SSE.add_ConnectorServicer_to_server(self, server) ## TW: This basically maps the functions and the "GetCapabilities", "ExecuteFunction" and "ExecuteScript" from the servicer to the gRPC server.

        if pem_dir: ## TW: If there are any authentication certificates:
            # Secure connection
            with open(os.path.join(pem_dir, 'sse_server_key.pem'), 'rb') as f:
                private_key = f.read()
            with open(os.path.join(pem_dir, 'sse_server_cert.pem'), 'rb') as f:
                cert_chain = f.read()
            with open(os.path.join(pem_dir, 'root_cert.pem'), 'rb') as f:
                root_cert = f.read()
            credentials = grpc.ssl_server_credentials([(private_key, cert_chain)], root_cert, True)
            server.add_secure_port('[::]:{}'.format(port), credentials)
            logging.info('*** Running server in secure mode on port: {} ***'.format(port))
        else:
            # Insecure connection
            server.add_insecure_port('[::]:{}'.format(port))
            logging.info('*** Running server in insecure mode on port: {} ***'.format(port))

        server.start() ## TW: Start the server (that will be used to service RPCs)
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            server.stop(0)


if __name__ == '__main__': ## TW: This checks that ExtensionsService_NBA is being run as the python file (and not imported as module)
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', nargs='?', default='50056') ## TW: Address/Port
    parser.add_argument('--pem_dir', nargs='?') ## TW: This is the location of authentication certs (? means "None")
    parser.add_argument('--definition-file', nargs='?', default='FuncDefs_OptimalAssignments.json') ## TW: This is where the functions are defined
    args = parser.parse_args()

    # need to locate the file when script is called from outside it's location dir.
    def_file = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), args.definition_file) ## Add  the location of the JSON function file

    calc = ExtensionService(def_file) ## TW: Instantiate a ConnectorServicer instance
    calc.Serve(args.port, args.pem_dir) ## TW: start the Server (plugin) at the specified port, with the specified authentication certs
