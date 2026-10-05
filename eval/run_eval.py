import json, urllib.request

questions=json.load(open("eval/goldset.json"))
base="http://localhost:8000"
correct=0
for q in questions:
    payload=json.dumps({"message":q["query"],"city":"Mysuru","language":q["lang"],"latitude":12.2958,"longitude":76.6394}).encode()
    req=urllib.request.Request(base+"/v1/chat",data=payload,headers={"Content-Type":"application/json"})
    try:
        data=json.load(urllib.request.urlopen(req,timeout=10))
        if data.get("answer"): correct+=1
    except Exception as e:
        print("FAIL",q["id"],e)
print(f"Fixture/live smoke score: {correct}/{len(questions)} = {correct/len(questions)*100:.1f}%")
print("This is an execution smoke test, not a scientific accuracy evaluation.")
