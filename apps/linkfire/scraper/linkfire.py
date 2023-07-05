from datetime import datetime
from apps.linkfire.scraper.function_linkfire_scrape import LinkfireScraper
from apps.linkfire.models import ScrapeLinkfires
from apps.common.constants import Timeformat


def linkfirescraper(username, password):
    try:
        profile = {"linkfire_username": username, "linkfire_password": password}
        scraper = LinkfireScraper(profile)
        # For each link that needs to be checked
        response = scraper.checklinkstoscrape()
        if not response:
            return
        for result in response:
            updated = True
            linkfireurl = result[0]
            linkfire_id = result[1]
            insights_shorttag = result[2]
            board_id = result[3]
            link_id = result[4]
            if not board_id:
                updated = False
                board_id = scraper.get_board_id()
            if not link_id:
                updated = False
                link_id = scraper.get_linkid(linkfireurl, board_id)
            if not insights_shorttag:
                updated = False
                insights_shorttag = scraper.insights_shorttag(board_id, link_id)

            # Set the link to lookup in the class
            if not all((board_id, link_id)):
                continue
            if not updated:
                ScrapeLinkfires.objects.filter(id=linkfire_id).update(
                    board_id=board_id,
                    link_id=link_id,
                    insights_shorttag=insights_shorttag,
                )

            validlink = scraper.setlookuplink(linkfireurl)
            if not validlink:
                continue

            # Before we start with the scrape, check if we already have up to date data in our database
            missingdates = scraper.checkexistingdata()
            if not missingdates:
                continue
            for date in missingdates:
                scraper.updatevariables()
                datefrom = date.strftime(Timeformat.ISO8601DATEFORMAT)
                today = datetime.now()
                today = today.strftime(Timeformat.ISO8601DATEFORMAT)
                scraper.getlocationsdata(
                    datefrom, datefrom, linkfire_id, date, board_id, link_id
                )
                scraper.getservicesdata(
                    datefrom, datefrom, linkfire_id, date, board_id, link_id
                )
    except Exception as e:
        scraper.handleerror(f"{'[LinkfireMainScraper] Could not Complete'}", str(e))
        raise e
