#!/usr/bin/env python3
"""e2_new.json의 자연스러운 E2로 엑셀 E2_이유 열만 교체(다른 셀·서식 불변)."""
import json, sys, openpyxl
def main(xlsx, e2json):
    new={d["pid"]: d["e2"] for d in json.load(open(e2json))}
    wb=openpyxl.load_workbook(xlsx)
    ws=wb.active
    hdr=[c.value for c in ws[1]]
    num_c=hdr.index("응답자번호")+1
    e2_c=hdr.index("E2_이유")+1
    n=0
    for row in ws.iter_rows(min_row=2):
        pid=int(row[num_c-1].value)-1   # 응답자번호 = pid+1
        if pid in new:
            ws.cell(row=row[0].row, column=e2_c).value=new[pid]; n+=1
    wb.save(xlsx)
    print(f"E2 교체 완료: {n}행")
if __name__=="__main__":
    main(sys.argv[1], sys.argv[2])
