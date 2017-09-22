# Toy Optimization
In this directory are files related to a less trivial Python SSE plugin for Qlik Sense. The problem is entirely fictitious but has
analogous application to many other real world resource opimization problems.

## Synopsis
You're company has to send its employees (or a subset) to a conference in Atlanta. Each employee has scored his/her preferences for 
travelling by various modes of transportation. Some employees perfer to go by Boat others by Car, etc. You are in the planning stages
and have the opportunity to buy a variety of tickets. You are tasked with assigning employees to tickets in such a way that you satisfy
as many of your employees as possible (by maximizing their overall satisfaction score).  
  
The following Qlik Sense Application will allow a user to input a given mix of tickets (plane, train, bus, boat) and output the best
assigment of employees to tickets.  
  
An example of some **Employee Preferences** look like the following:  

| Employee     | Plane | Train | Bus   | Boat   |
| ------------ | :---: | :---: | :---: | :----: |
| Sam Smith    | 10    | 6     | 1     | 1      |
| Joanna Frink | 2     | 9     | 7     | 4      |
| ...          | ...   | ...   | ...   | ...    |

## Solution
This can be formulated as a simple **Integer Program**. The formulation for the problem is below.

![](OptimizationFormulation.gif?raw=true "Title")
