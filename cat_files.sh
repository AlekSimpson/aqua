#!/bin/bash 

cat Error.swift Lexer.swift Node.swift Parser.swift Tokens.swift Run.swift > main.swift 
clear 
swift main.swift
