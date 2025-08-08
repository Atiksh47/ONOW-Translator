import requests

# Update the URL to the new async HTTP endpoint
url = "http://localhost:7071/api/enqueue-transcription"
payload = {
    "file_url": "https://cdn.fbsbx.com/v/t59.3654-21/522625396_1073834248060074_3630661123320522815_n.mp4/audioclip-1753325936000-24335.mp4?_nc_cat=100&ccb=1-7&_nc_sid=d61c36&_nc_ohc=q3SOZlVsGREQ7kNvwFrblgD&_nc_oc=AdnltkkljC9R6bJJHBVh49sgE0bShawdXxGXuF5EJgrkpPNd12YSg_WA94KdFfvoLGbAU8wyD0L_6ghhlaAjqti3&_nc_zt=28&_nc_ht=cdn.fbsbx.com&_nc_gid=NRCR3dcYG6gimmzlrxAvTQ&oh=03_Q7cD2wFt1_39qjkSfrBdD0z0ZFEeEAR6E55SIKkuMvac3ObsVA&oe=68836B5B",
    "country": "India"
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("Response:", response.text)
