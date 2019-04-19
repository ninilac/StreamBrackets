import clr
import sys
import json
import os
import ctypes
import codecs
import math

ScriptName = "Stream Brackets"
Website = "https://github.com/ninilac/StreamBrackets"
Description = "Tournament and betting commands for Streamlabs Chatbot"
Creator = "Ninilac"
Version = "0.0.6"

configFile = "config.json"
settings = {}

question = ""
options = []
bets = {}
UserBets = {}
isFighting = False
isLocked = False
isMulti = False
betMultiplier = 2.0

currencies = {}

def Is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False

def GiveReward(winner):
    global bets

    winnerList = ""
    for bet in bets[winner]:
        if bet is not None:
            user = bet[0]
            username = bet[1]
            amount = int(math.floor(bet[2]*betMultiplier))
            currencies[user] += amount
            winnerString = "{}({}),".format(username, amount)
            winnerList += winnerString
    winnerList = winnerList[0:len(winnerList)-1]
    return winnerList

def ParseOptions():
    global options
    optionList = ""
    for o in options:
        optionList += o + ", "
    return optionList[:-2]

def ParseStartBetCommand(message, command):
    message = message.strip().split(" ")
    inQuestion = False
    parameters = []
    question = ""
    for i in range(1, len(message)):
        if i == 1:
            if (message[i][0] == '"' or message[i][0] == "'"):
                inQuestion = True
                question += message[i][1:]
            else:
                parameters.append("")
        elif inQuestion:
            if message[i][-1:] == '"' or message[i][-1:] == "'":
                inQuestion = False
                question += " " + message[i][:-1]
                parameters.append(question.lower())
            else:
                question += " " + message[i]
        else:
            parameters.append(message[i].lower())
    if len(parameters) < 3:
        Parent.SendStreamMessage("not enough parameters: {} \"[Question]\" [Option_1] [Option_2] [Bet Multiplier] [isMulti]".format(command))
        return [], False
    return parameters, True


def EndFight():
    global bets
    global UserBets
    global options
    global isFighting
    global isLocked
    global isMulti
    global betMultiplier

    bets = {}
    UserBets = {}
    options = []
    isFighting = False
    betMultiplier = 2.0
    isLocked = False
    isMulti = False
    return

def ScriptToggled(state):
    return

def Init():
    global settings

    path = os.path.dirname(__file__)
    try:
        with codecs.open(os.path.join(path, configFile), encoding='utf-8-sig', mode='r') as file:
            settings = json.load(file, encoding='utf-8-sig')
    except:
        Parent.Log("StreamBrackets", "Couldn't find config file, loading default config.")
        settings = {
            "liveOnly": True,
            "fightCommand": "!sbfight",
            "viewCommand": "!sbview",
            "lockCommand": "!sblock",
            "betCommand": "!sbbet",
            "deleteCommand": "!sbdelete",
            "winCommand": "!sbwin",
            "cancelCommands": "!sbcancel",
            "fightPermission": "Moderator",
            "betPermission": "Everyone",
            "winPermission": "Moderator",
            "cancelPermissions": "Moderator",
            # currency settings
            "currencyCommand": "!sbcoin",
            "startCurrency": 500,
            "currencyPermission": "Everyone",
            "currencyAddPermission": "Moderator",
            "currencyRemovePermission": "Moderator",
            "MyFile": "sbCurrency.txt"
        }

    ParseCurrency()

    return


def SaveCurrency():
    defaultFile = "sbCurrency.txt"
    f = ""
    if "MyFile" in settings.keys():
        f = open(settings["MyFile"], "w")
    else:
        f = open(defaultFile)
    for curr in currencies.keys():
        f.write("{},{}\n".format(curr, currencies[curr]))
    f.close()
    return

def ParseCurrency():
    file = "sbCurrency.txt"
    if "MyFile" in settings.keys():
        file = settings["MyFile"]
    if os.path.isfile(file):
        with open(file) as openfileobject:
            for line in openfileobject:
                elements = line.split(',')
                if len(elements) != 2 or not Is_number(elements[1]):
                    break
                currencies[elements[0]] = int(elements[1])
    else:
        f = open(file, "w+")
        f.close()
    return

def HasBet(userBetList):
    for bet in userBetList:
        if bet[0] in options:
            return True
    return False

def DeleteBet(data, betOption):
    found = False
    for i in range(0, len(UserBets[data.User])):
        userBet = UserBets[data.User][i]
        if userBet[0] == betOption:
            bet = bets[userBet[0]][userBet[1]]
            refund = bet[2]
            currencies[bet[0]] = currencies[bet[0]] + refund
            bets[userBet[0]][userBet[1]] = None
            UserBets[data.User][i] = ("", 0)
            currencyName = settings["currencyCommand"][1:len(settings["currencyCommand"])]
            Parent.SendStreamMessage("{}, deleted bet for {}, you were refunded {} {}".format(data.UserName, betOption, refund, currencyName))
            found = True
            break
    if not found:
        Parent.SendStreamMessage("{}, You currently have no bet for {}".format(data.UserName, betOption))

def Execute(data):
    global bets
    global UserBets
    global question
    global options
    global isFighting
    global isLocked
    global isMulti
    global betMultiplier

    if data.User not in currencies.keys():
        currencies[data.User] = settings["startCurrency"]

    if data.IsChatMessage() and (Parent.IsLive() or not settings["liveOnly"]):
        command = data.GetParam(0).lower()
        # Create Command
        if command == settings["fightCommand"] and Parent.HasPermission(data.User, settings["fightPermission"], ""):
            (parameters, success) = ParseStartBetCommand(data.Message, command)
            if not success:
                return
            if isFighting:
                Parent.SendStreamMessage("A bet is currently going on, use \"{}\" to cancel it".format(settings["cancelCommand"]))
            else:
                question = parameters[0]
                isFighting = True
                for i in range(1, len(parameters)):
                    if i == 4 and Is_number(parameters[i]):
                        betMultiplier = float(parameters[i])
                    if i == 5 and parameters[i].lower() == "multi":
                        isMulti = True
                    else:
                        options.append(parameters[i])
                        bets[parameters[i]] = []
                optionsList = ParseOptions()
                Parent.SendStreamMessage("{} Bet between {}. your bets will be multiplied by {} if you guess correctly!".format(question, optionsList, betMultiplier))

        elif command == settings["viewCommand"] and Parent.HasPermission(data.User, settings["betPermission"], ""):
            if not isFighting:
                Parent.SendStreamMessage("No bet is currently taking place, use \"{} [option_1] [option_2]\" to start a new bet".format(settings["fightCommand"]))
            else:
                optionsList = ParseOptions()
                betList = ""
                foundBet = False
                if data.User in UserBets:
                    for userBet in UserBets[data.User]:
                        if userBet[0] in bets:
                            Parent.Log("StreamBrackets", "[info]" + userBet[0] + str(userBet[1]))
                            betList += userBet[0] + " (" + str(bets[userBet[0]][userBet[1]][2]) + "), "
                            foundBet = True
                    if len(betList) > 1:
                        betList = betList[:-2]
                Parent.SendStreamMessage("Current bet: {} Bet between {}. your bets will be multiplied by {} if you guess correctly!".format(question, optionsList, betMultiplier))
                if foundBet:
                    Parent.SendStreamMessage("{} here are you current bets: {}".format(data.UserName, betList))

        elif command == settings["deleteCommand"] and Parent.HasPermission(data.User, settings["betPermission"], ""):
            betOption = data.GetParam(1)
            if not isFighting:
                Parent.SendStreamMessage("No bet is currently taking place, use \"{} [option_1] [option_2]\" to start a new bet".format(settings["fightCommand"]))
            if isLocked:
                Parent.SendStreamMessage("Bets are currently locked, you cannot delete a bet right now.".format(settings["fightCommand"]))
            elif data.GetParamCount() < 2:
                Parent.SendStreamMessage("Not enough parameters: {} [Option]".format(command))
            elif betOption not in bets.keys():
                Parent.SendStreamMessage("{} is not a betting option right now".format(betOption))
            else:
                DeleteBet(data, betOption)

        elif command == settings["lockCommand"] and Parent.HasPermission(data.User, settings["lockPermission"], ""):
            if not isFighting:
                Parent.SendStreamMessage("No bet is currently taking place, use \"{} [option_1] [option_2]\" to start a new bet".format(settings["fightCommand"]))
            else:
                isLocked = True
                Parent.SendStreamMessage("Bets are locked for bet \"{}\"".format(question))

        elif command == settings["betCommand"] and Parent.HasPermission(data.User, settings["betPermission"], ""):
            currencyName = settings["currencyCommand"][1:len(settings["currencyCommand"])]
            if data.GetParamCount() < 3:
                Parent.SendStreamMessage("Not enough parameters: {} [Option] [Amount]".format(command))
            elif not isFighting:
                Parent.SendStreamMessage("No bet is currently taking place, use \"{} [option_1] [option_2]\" to start a new bet".format(settings["fightCommand"]))
            elif isLocked:
                Parent.SendStreamMessage("Bets are currently locked.")
            else:
                betOption = data.GetParam(1).lower()
                if not Is_number(data.GetParam(2)):
                    Parent.SendStreamMessage("The amount entered is not a valid number.")
                    return
                betAmount = int(data.GetParam(2))
                if betAmount > currencies[data.User]:
                    Parent.SendStreamMessage("{0}, you don't have enough {1}, you currently have {2} {1}".format(data.UserName, currencyName, currencies[data.User]))
                    return
                if betOption in bets.keys():
                    found = False
                    if data.User not in UserBets:
                        Parent.Log("sb", "not cool")
                        UserBets[data.User] = []
                    else:
                        for userBet in UserBets[data.User]:
                            Parent.Log("sb", "[INFO]" + userBet[0] + ", " + betOption)
                            if userBet[0] == betOption and userBet[0] != "":
                                found = True
                                currencies[data.User] = currencies[data.User] - betAmount
                                prevBet = bets[betOption][userBet[1]]
                                bets[betOption][userBet[1]] = (prevBet[0], prevBet[1], prevBet[2] + betAmount)
                                Parent.SendStreamMessage("{0} just added {1} {2} on his bet on {3}, total bet: {4}".format(data.UserName, betAmount, currencyName, betOption, bets[betOption][userBet[1]][2]))
                                break
                    if not found:
                        if not isMulti and HasBet(UserBets[data.User]):
                            for opt in UserBets[data.User]:
                                if opt[0] in options:
                                    DeleteBet(data, opt[0])
                        currencies[data.User] = currencies[data.User] - betAmount
                        bets[betOption].append((data.User, data.UserName, betAmount))
                        UserBets[data.User].append((betOption, len(bets[betOption])-1))
                        Parent.SendStreamMessage("{0} just bet {1} {2} on {3}".format(data.UserName, betAmount, currencyName, betOption))
                else:
                    optionsList = ParseOptions()
                    Parent.SendStreamMessage("{} is not currently a betting option. here's the current bet: {} {}".format(betOption, question, optionsList))

        elif command == settings["winCommand"] and Parent.HasPermission(data.User, settings["winPermission"], ""):
            if data.GetParamCount() < 2:
                Parent.SendStreamMessage("Not enough parameters: {} [Option]".format(command))
            elif not isFighting:
                Parent.SendStreamMessage("No bet is currently taking place, use \"{} [option_1] [option_2]\" to start a new bet".format(settings["fightCommand"]))
            else:
                winner = data.GetParam(1).lower()
                if winner not in options:
                    optionsList = ParseOptions()
                    Parent.SendStreamMessage("{} is not currently a betting option. here's the current bet: {} {}".format(winner, question, optionsList))
                    return
                response = "{} has won! The following viewers have won their bet: $betWinners".format(winner)
                winnerList = GiveReward(winner)
                response = response.replace("$betWinners", winnerList)
                Parent.SendStreamMessage(response)
                EndFight()

        elif command == settings["cancelCommand"] and Parent.HasPermission(data.User, settings["cancelPermission"], ""):
            Parent.SendStreamMessage("Bet \"{}\" was cancelled. All bets were refunded".format(question))
            for option in bets.keys():
                for bet in bets[option]:
                    if bet is not None:
                        currencies[bet[0]] = currencies[bet[0]] + bet[2]
            EndFight()

        elif command == settings["currencyCommand"] and Parent.HasPermission(data.User, settings["currencyPermission"], ""):
            currencyName = settings["currencyCommand"][1:len(settings["currencyCommand"])]
            if data.GetParamCount() < 2:
                if data.User not in currencies.keys():
                    currencies[data.User] = int(settings["startCurrency"])
                Parent.SendStreamMessage(
                    "{}, you currently have {} {}".format(data.UserName, currencies[data.User], currencyName))
            else:
                arg1 = data.GetParam(1).lower()

                if arg1 == "add" and Parent.HasPermission(data.User, settings["currencyAddPermission"], ""):
                    if data.GetParamCount() < 4 or not Is_number(data.GetParam(3)):
                        Parent.SendStreamMessage("Not enough parameters: {} [User] [Amount]".format(command))
                        return
                    viewerList = Parent.GetViewerList()
                    user = data.GetParam(2).lower()
                    if user not in viewerList:
                        Parent.SendStreamMessage("Invalid User: {}".format(data.GetParam(2).lower()))
                        return
                    addedCurrency = int(data.GetParam(3))
                    currencies[user] = currencies[user] + addedCurrency
                    Parent.SendStreamMessage("Added {0} {1} to {2}'s account, they now have {3} {1}".format(addedCurrency, currencyName, Parent.GetDisplayName(user), currencies[user]))

                elif arg1 == "remove" and Parent.HasPermission(data.User, settings["currencyRemovePermission"], ""):
                    if data.GetParamCount() < 4 or not Is_number(data.GetParam(3)):
                        Parent.SendStreamMessage("Not enough parameters: {} [User] [Amount]".format(command))
                        return
                    viewerList = Parent.GetViewerList()
                    user = data.GetParam(2).lower()
                    if user not in viewerList:
                        Parent.SendStreamMessage("Invalid User: {}".format(data.GetParam(2).lower()))
                        return
                    removedCurrency = int(data.GetParam(3))
                    currencies[user] = currencies[user] - removedCurrency
                    Parent.SendStreamMessage("Removed {0} {1} to {2}'s account, they now have {3} {1}".format(removedCurrency, currencyName, Parent.GetDisplayName(user), currencies[user]))

        SaveCurrency()
    return

def ReloadSettings(jsonData):
    Init()
    return

def OpenReadMe():
    location = os.path.join(os.path.dirname(__file__), "README.txt")
    os.startfile(location)
    return

def Tick():
    return
