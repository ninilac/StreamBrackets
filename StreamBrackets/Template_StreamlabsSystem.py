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
Version = "0.0.1"

configFile = "config.json"
settings = {}

fighter1 = ""
fighter2 = ""
bets = {}
isFighting = False
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
        user = bet[0]
        username = bet[1]
        amount = int(math.floor(bet[2]*betMultiplier))
        currencies[user] += amount
        winnerString = "{}({}),".format(username, amount)
        winnerList += winnerString
    winnerList = winnerList[0:len(winnerList)-1]
    return winnerList

def EndFight():
    global bets
    global fighter1
    global fighter2
    global isFighting
    global betMultiplier

    bets = {}
    fighter1 = ""
    fighter2 = ""
    isFighting = False
    betMultiplier = 2.0
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
        settings = {
            "liveOnly": True,
            "fightCommand": "!sbfight",
            "betCommand": "!sbbet",
            "winCommand": "!sbwin",
            "cancelCommands": "!sbcancel",
            "fightPermission": "Moderator",
            "betPermission": "Everyone",
            "winPermission": "Moderator",
            "cancelPermissions": "Moderator",
            # currency settings
            "currencyCommand": "!sbcoin",
            "startCurrency": 500,
            "MyPermission": "Everyone",
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
    with open(file) as openfileobject:
        for line in openfileobject:
            elements = line.split(',')
            if len(elements) != 2 or not Is_number(elements[1]):
                break
            currencies[elements[0]] = int(elements[1])
    return

def Execute(data):
    global bets
    global fighter1
    global fighter2
    global isFighting
    global betMultiplier

    if data.User not in currencies.keys():
        currencies[data.User] = settings["startCurrency"]

    if data.IsChatMessage() and (Parent.IsLive() or not settings["liveOnly"]):
        command = data.GetParam(0).lower()
        # Create Command
        if command == settings["fightCommand"] and Parent.HasPermission(data.User, settings["fightPermission"], ""):
            if data.GetParamCount() < 3:
                Parent.SendStreamMessage("Not enough parameters: {} [fighter_1] [fighter_2] [betMultiplier]".format(command))
            elif isFighting:
                Parent.SendStreamMessage("A fight is currently going on, use '{}' to cancel it".format(settings["cancelCommand"]))
            else:
                fighter1 = data.GetParam(1).lower()
                fighter2 = data.GetParam(2).lower()
                isFighting = True
                bets = {
                    fighter1: [],
                    fighter2: []
                }
                if data.GetParamCount() == 4 and Is_number(data.GetParam(3)):
                    betMultiplier = float(data.GetParam(3))
                Parent.SendStreamMessage("Fight is on between {} and {}, your bets will be multiplied by {} if you guess correctly!".format(fighter1, fighter2, betMultiplier))

        elif command == settings["betCommand"] and Parent.HasPermission(data.User, settings["betPermission"], ""):
            currencyName = settings["currencyCommand"][1:len(settings["currencyCommand"])]
            if data.GetParamCount() < 3:
                Parent.SendStreamMessage("Not enough parameters: {} [fighter] [Amount]".format(command))
            elif not isFighting:
                Parent.SendStreamMessage("No fight is currently taking place, use '{} [fighter_1] [fighter_2]' to start a new fight".format(settings["fightCommand"]))
            else:
                fighterBet = data.GetParam(1).lower()
                if not Is_number(data.GetParam(2)):
                    Parent.SendStreamMessage("The amount entered is not a valid number.")
                    return
                betAmount = int(data.GetParam(2))

                if betAmount > currencies[data.User]:
                    Parent.SendStreamMessage("{0}, you don't have enough {1}, you currently have {2} {1}".format(data.UserName, currencyName, currencies[data.User]))
                    return

                if fighterBet == fighter1:
                    currencies[data.User] = currencies[data.User] - betAmount
                    bets[fighter1].append((data.User, data.UserName, betAmount))
                    Parent.SendStreamMessage("{0} just betted {1} {2} on {3}".format(data.UserName, betAmount, currencyName, fighter1))

                elif fighterBet == fighter2:
                    currencies[data.User] = currencies[data.User] - betAmount
                    bets[fighter2].append((data.User, data.UserName, betAmount))
                    Parent.SendStreamMessage("{0} just betted {1} {2} on {3}".format(data.UserName, betAmount, currencyName, fighter2))
                else:
                    Parent.SendStreamMessage("Fighter {} is not currently fighting".format(fighterBet))

        elif command == settings["winCommand"] and Parent.HasPermission(data.User, settings["winPermission"], ""):
            if data.GetParamCount() < 2:
                Parent.SendStreamMessage("Not enough parameters: {} [fighter]".format(command))
            elif not isFighting:
                Parent.SendStreamMessage("No fight is currently taking place, use '{} [fighter_1] [fighter_2]' to start a new fight".format(settings["fightCommand"]))
            else:
                winner = data.GetParam(1).lower()
                if winner != fighter1 and winner != fighter2:
                    Parent.SendStreamMessage("{} is not currently fighting. here are the current fighters: {}, {}".format(winner, fighter1, fighter2))
                    return
                response = "{} has won! The following viewers have won their bet: $betWinners".format(fighter1)
                winnerList = GiveReward(winner)
                response = response.replace("$betWinners", winnerList)
                Parent.SendStreamMessage(response)
                EndFight()

        elif command == settings["cancelCommand"] and Parent.HasPermission(data.User, settings["cancelPermission"], ""):
            Parent.SendStreamMessage("Fight between {} and {} was cancelled. Everyone's bets was refunded".format(fighter1, fighter2))
            for bet in bets[fighter1]:
                currencies[bet[0]] = currencies[bet[0]] + bet[2]
            for bet in bets[fighter2]:
                currencies[bet[0]] = currencies[bet[0]] + bet[2]
            EndFight()

        elif command == settings["currencyCommand"] and Parent.HasPermission(data.User, settings["MyPermission"], ""):
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
