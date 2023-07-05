import sys
import os
from decimal import Decimal
import time
import datetime
from apps.common.models import DailyAdspendGenre
import xlsxwriter
from datetime import timedelta

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "Tiktok")))
# import Tiktok_api_handler as tt

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "Facebook")))
# import Facebook_api_handler as fb

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "Snapchat")))
# import Snapchat_api_handler as sc

# sys.path.insert(
#     0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../Database"))
# )
# import DatabaseClass as DB


def createExcel(platformConn, date):
    filename = "Spend Data " + str(date) + ".xlsx"
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({"bold": True})
    datetime_format = workbook.add_format({"num_format": "dd/mm/yy hh:mm"})
    money = workbook.add_format({"num_format": "€#.##"})
    # Create FB Header and date
    worksheet.write("A1", "Facebook", bold)
    worksheet.write("C1", str(date), bold)
    # Get FB data
    spendData = DailyAdspendGenre.objects.filter(
        platform="Facebook", date=date
    ).values_list("scraper_group_id", "spend")
    row = 1
    col = 1
    notFound = None
    for data in spendData:
        genre = data[0]
        spend = data[1]
        if genre == "NULL" or genre == None:
            # Filter Follower campaign and save to append to end of file
            notFound = data
        else:
            worksheet.write(row, col, genre)
            worksheet.write(row, col + 1, Decimal(spend), money)
            row += 1
    # Add Not Found to the end
    if notFound != None:
        spend = notFound[1]
    else:
        spend = 0
    notFound = None
    worksheet.write(row, 0, "", bold)
    worksheet.write(row, 1, "General/No genre")
    worksheet.write(row, 2, Decimal(spend), money)
    row += 1
    # Create TT Header
    worksheet.write(row, 0, "Tiktok", bold)
    # Get TT data
    spendData = DailyAdspendGenre.objects.filter(
        platform="Tiktok", date=date
    ).values_list("scraper_group_id", "spend")
    followerCampaign = None
    for data in spendData:
        genre = data[0]
        spend = data[1]
        if genre == "NULL" or genre == None:
            # Filter Follower campaign and save to append to end of file
            followerCampaign = data
        else:
            worksheet.write(row, col, genre)
            worksheet.write(row, col + 1, Decimal(spend), money)
            row += 1
    # Add Follower campaign to the end
    if followerCampaign != None:
        spend = followerCampaign[1]
    else:
        spend = 0
    worksheet.write(row, 0, "Tiktok Followers", bold)
    worksheet.write(row, 1, "Followers/No genre")
    worksheet.write(row, 2, Decimal(spend), money)
    row += 1

    # Create SC Header
    worksheet.write(row, 0, "Snap", bold)
    # Get SC data
    spendData = DailyAdspendGenre.objects.filter(
        platform="Snap", date=date
    ).values_list("scraper_group_id", "spend")
    followerCampaign = None
    for data in spendData:
        genre = data[0]
        spend = data[1]
        if genre == "NULL" or genre == None:
            # Filter Follower campaign and save to append to end of file
            followerCampaign = data
        else:
            worksheet.write(row, col, genre)
            worksheet.write(row, col + 1, Decimal(spend), money)
            row += 1
    # Add Not Found to the end
    if notFound != None:
        spend = notFound[1]
    else:
        spend = 0

    workbook.close()


if __name__ == "__main__":
    live = False
    if "-d" in sys.argv[1:]:
        debug = True
    else:
        debug = False
    if "-l" in sys.argv[1:]:
        live = True
    else:
        live = False
        print(
            "[TEST MODE] Type 1 if you want to connect to your LOCALHOST. Type 2 if you want to connect to our LIVE TESTING ENVIRONMENT for testenv.strangefruits.net"
        )
        answer = input()
        if answer == "1":
            databaseType = "local_ads"
        elif answer == "2":
            databaseType = "testenv_ads"
        else:
            print("Not a valid input. Abort.")
            exit()
    if "-e" in sys.argv[1:]:
        excel = True
    else:
        excel = False
    if excel == False:
        print("Er wordt geen excel sheet gemaakt. Voeg -e toe om dit wel toe doen")
    if live:
        print(
            "Let op! Je gaat nu de optimizer op de live database runnen. \nAls dit inderdaad de bedoeling is, type 'Yes'. Type anders 'No'. Druk daarna op Enter."
        )
        answer = input()
        if answer == "Yes":
            databaseType = "ads"
        else:
            print(
                "Als je op de locale database wil runnen, gebruik dan NIET de '-l' flag"
            )
            exit()

    now = datetime.datetime.now() - timedelta(days=1)
    lastDate = now.date()
    database = DB.Database(databaseType)

    print("[Main] Starting mainloop")
    turn_off = "No"
    while True:
        try:
            turn_off = database.execSQL(
                """SELECT `value` FROM `settings` WHERE `variable` = 'turn_off' """,
                (),
                False,
            )[0][0]
        except Exception as e:
            print("[Main] Could not get turn_off value from database " + repr(e))
        if turn_off == "Yes":
            print("[Main] Turning off")
            break
        now = datetime.datetime.now()
        if lastDate < now.date():
            activateTime = now.replace(hour=9, minute=5)
            if activateTime <= now:
                print(
                    "It is now "
                    + str(now)
                    + ". We will start updating spend data and write it to an excel file."
                )
                database = DB.Database(databaseType)
                # Check from what platforms we have the auth keys
                enabled_platforms = database.execSQL(
                    """SELECT platform FROM authkeys GROUP BY platform;""", (), False
                )
                if len(enabled_platforms) == 0:
                    print(
                        "[No Auth Keys] Sleeping because we found no auth keys. Checking again in 1 min..."
                    )
                    time.sleep(60)
                    continue
                enabled_platforms_list = []
                for x in enabled_platforms:
                    enabled_platforms_list.append(x[0].lower())
                if "tiktok" in enabled_platforms_list:
                    print("[Tiktok Adspend] Retrieving TikTok adspend...")
                    tiktok = tt.TikTokAPI(database, debug)
                    try:
                        tiktok.updateDailySpendData()
                    except Exception as e:
                        tiktok.handleError(
                            "[Daily Adspend Updater] Tiktok error",
                            "Could not update daily spend data for Tiktok due to the following error: \n"
                            + repr(e),
                            "High",
                        )

                if "facebook" in enabled_platforms_list:
                    print("[Facebook Adspend] Retrieving Facebook adspend...")
                    facebook = fb.FacebookAPI(database, debug)
                    try:
                        facebook.updateDailySpendData()
                    except Exception as e:
                        facebook.handleError(
                            "[Daily Adspend Updater] Facebook error",
                            "Could not update daily spend data for Facebook due to the following error: \n"
                            + repr(e),
                            "High",
                        )
                if "snap" in enabled_platforms_list:
                    print("[Snap Adspend] Retrieving Snap adspend...")
                    snapchat = sc.SnapchatAPI(database, debug)
                    try:
                        snapchat.updateDailySpendData()
                    except Exception as e:
                        snapchat.handleError(
                            "[Daily Adspend Updater] Facebook error",
                            "Could not update daily spend data for Facebook due to the following error: \n"
                            + repr(e),
                            "High",
                        )

                if excel:
                    createExcel(facebook, lastDate)
                lastDate = now.date()
                print("Done!")
            else:
                time.sleep(5 * 60)
        else:
            time.sleep(5 * 60)
