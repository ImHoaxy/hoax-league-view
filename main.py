from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
REGION_ROUTING = "europe"
PLATFORM_ROUTING = "euw1"
BASE_HEADERS = {"X-Riot-Token": RIOT_API_KEY}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("Using Riot API key:", RIOT_API_KEY)

@app.get("/account")
async def get_account(gameName: str = Query(..., description="Riot ID (in-game name)"),
                      tagLine: str = Query(..., description="Riot Tag (the tag after #)")):
    # Step 1: Get Riot account info by Riot ID + Tagline
    url_account = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url_account, headers=BASE_HEADERS)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Account fetch failed: {resp.text}")
        account_data = resp.json()

        puuid = account_data.get("puuid")
        if not puuid:
            raise HTTPException(status_code=404, detail="PUUID not found in account data")

        # Step 2: Get summoner info by PUUID
        url_summoner = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        summoner_resp = await client.get(url_summoner, headers=BASE_HEADERS)
        print("Summoner response status:", summoner_resp.status_code)
        print("Summoner JSON:", summoner_resp.text)

        if summoner_resp.status_code != 200:
            raise HTTPException(status_code=summoner_resp.status_code, detail=f"Summoner fetch failed: {summoner_resp.text}")
        summoner = summoner_resp.json()

        # Step 3: Get rank info by summoner ID
        summoner_id = summoner.get("id")
        url_rank = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        summoner = summoner_resp.json()
        summoner_id = summoner.get("id")
        print("Using summonerId for rank fetch:", summoner_id)

        rank_resp = await client.get(url_rank, headers={"X-Riot-Token": RIOT_API_KEY})

        if rank_resp.status_code != 200:
            raise HTTPException(status_code=rank_resp.status_code, detail=f"Rank fetch failed: {rank_resp.text}")
        ranks = rank_resp.json()

        # Step 4: Get last 3 matches by PUUID
        url_matches_ids = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=3"
        matches_ids_resp = await client.get(url_matches_ids, headers=BASE_HEADERS)
        if matches_ids_resp.status_code != 200:
            raise HTTPException(status_code=matches_ids_resp.status_code, detail=f"Matches IDs fetch failed: {matches_ids_resp.text}")
        match_ids = matches_ids_resp.json()

        matches = []
        for match_id in match_ids:
            url_match = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            match_resp = await client.get(url_match, headers=BASE_HEADERS)
            if match_resp.status_code == 200:
                matches.append(match_resp.json())

        # Return aggregated data
        return {
            "account": account_data,
            "summoner": summoner,
            "ranks": ranks,
            "matches": matches
        }
