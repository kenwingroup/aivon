import collections,hashlib,json,re,unicodedata
from pathlib import Path
HERE=Path(__file__).parent

def clean(s):return re.sub(r'[ \t]+',' ',unicodedata.normalize('NFC',str(s or '')).replace('\r\n','\n')).strip()
def norm(s):
    s=unicodedata.normalize('NFD',clean(s).lower().replace('đ','d'))
    return re.sub(r'[^a-z0-9]+',' ',''.join(c for c in s if unicodedata.category(c)!='Mn')).strip()
NORTH=['Hà Nội','Hải Phòng','Bắc Ninh','Bắc Giang','Hưng Yên','Hải Dương','Quảng Ninh','Thái Bình','Nam Định','Ninh Bình','Hà Nam','Hòa Bình','Phú Thọ','Vĩnh Phúc','Thái Nguyên','Bắc Kạn','Tuyên Quang','Hà Giang','Cao Bằng','Lạng Sơn','Lào Cai','Yên Bái','Sơn La','Điện Biên','Lai Châu']
CENTRAL=['Thanh Hóa','Nghệ An','Hà Tĩnh','Quảng Bình','Quảng Trị','Huế','Đà Nẵng','Quảng Nam','Quảng Ngãi','Bình Định','Phú Yên','Khánh Hòa','Ninh Thuận','Bình Thuận','Kon Tum','Gia Lai','Đắk Lắk','Đắk Nông','Lâm Đồng']
SOUTH=['Hồ Chí Minh','Bình Dương','Đồng Nai','Bình Phước','Tây Ninh','Bà Rịa Vũng Tàu','Long An','Tiền Giang','Bến Tre','Trà Vinh','Vĩnh Long','Đồng Tháp','An Giang','Kiên Giang','Cần Thơ','Hậu Giang','Sóc Trăng','Bạc Liêu','Cà Mau']
HN_AREAS=['Ba Đình','Bắc Từ Liêm','Nam Từ Liêm','Từ Liêm','Cầu Giấy','Đống Đa','Hà Đông','Hai Bà Trưng','Hoàn Kiếm','Hoàng Mai','Long Biên','Tây Hồ','Thanh Xuân','Ba Vì','Chương Mỹ','Đan Phượng','Đông Anh','Gia Lâm','Hoài Đức','Mê Linh','Mỹ Đức','Phú Xuyên','Phúc Thọ','Quốc Oai','Sóc Sơn','Sơn Tây','Thạch Thất','Thanh Oai','Thanh Trì','Thường Tín','Ứng Hòa']
REGIONS={norm(p):('Miền Bắc' if p in NORTH else 'Miền Trung' if p in CENTRAL else 'Miền Nam') for p in NORTH+CENTRAL+SOUTH}
NAMES={norm(p):p for p in NORTH+CENTRAL+SOUTH}
TRANSPORT=re.compile(r'\b(nha xe|xe|ben|cang|ghep|gui hang|giao hang|van chuyen|lai xe)\b')

def contains(text,phrase):return (' '+norm(phrase)+' ') in (' '+norm(text)+' ')
def geography(address,area,section,source_region):
    a=norm(address);e=norm(area);h=norm(section)
    has_domestic=any(contains(a,p) for p in NORTH+CENTRAL+SOUTH)
    if not has_domestic and (contains(a,'viêng chăn') or contains(a,'xaythany') or e=='lao' or
        (re.search(r'(?:,|\s)(?:lao|laos)$',a) and not any(contains(a,p) for p in NORTH+CENTRAL+SOUTH) and e not in [norm(p) for p in HN_AREAS])):
        return 'Ngoài Việt Nam','Lào','',[], 'địa chỉ/khu vực nguồn'
    found=[p for k,p in NAMES.items() if (' '+k+' ') in (' '+a+' ')]
    if 'hue' in a and not found:found=['Huế']
    area_prov=[p for k,p in NAMES.items() if e==k or e=='tp '+k or e=='tinh '+k]
    if e in ('hn','ha noi'):area_prov=['Hà Nội']
    areas=[p for p in HN_AREAS if contains(address,p)]
    issues=[]
    if has_domestic and e=='lao':issues.append('Ô khu vực ghi Lào nhưng địa chỉ ghi Việt Nam; cần xác minh địa điểm thực tế')
    if len(found)==1:province=found[0];evidence='địa chỉ nguồn'
    elif len(found)>1:
        # Commune/road names such as Đồng Tháp or Hòa Bình occur inside Hà Nội addresses.
        # Prefer an explicitly labelled province, else the final province name in the address.
        explicit=[p for p in found if re.search(r'\b(?:tinh|tp|thanh pho) '+re.escape(norm(p))+r'\b',a)]
        choices=explicit or found
        province=max(choices,key=lambda p:a.rfind(norm(p)))
        evidence='tỉnh/TP ghi rõ hoặc cuối địa chỉ nguồn'
    elif area_prov:province=area_prov[0];evidence='khu vực nguồn'
    elif (e in [norm(p) for p in HN_AREAS]) or contains(a,'HN') or contains(a,'Hà Nội') or areas:
        province='Hà Nội';evidence='quận/huyện hoặc viết tắt trong nguồn'
    else:
        found_section=[p for k,p in NAMES.items() if (' '+k+' ') in (' '+h+' ')]
        province=found_section[0] if len(found_section)==1 else '';evidence='tiêu đề khu vực nguồn' if province else 'chưa có tỉnh/TP rõ'
    if province and area_prov and province!=area_prov[0]:issues.append('Tỉnh/TP trong địa chỉ khác ô khu vực; giữ cả thông tin gốc để xác minh')
    region=REGIONS.get(norm(province),source_region)
    if province and region!=source_region:issues.append('Địa chỉ thuộc '+region+' nhưng nằm trong file '+source_region)
    district=''
    if province=='Hà Nội':
        district=max(areas,key=len) if areas else (next((p for p in HN_AREAS if norm(p)==e),'') or '')
    if not district and area and not TRANSPORT.search(e) and norm(area)!=norm(province):district=area
    if not province:issues.append('Chưa xác định được tỉnh/TP từ nguồn')
    return region,province,district,issues,evidence

# A phone candidate may contain spaces/dots. Never prepend digits to a short number.
PHONE_TOKEN=re.compile(r'(?<!\d)(?:\+?\d[\d .()]*\d)(?!\d)')
def phones(text,country='VN'):
    valid=[];invalid=[]
    for m in PHONE_TOKEN.finditer(clean(text)):
        raw=m.group().strip();digits=re.sub(r'\D','',raw)
        if len(digits)<8:continue
        value=''
        if country=='Lào' and digits.startswith('00856') and 13<=len(digits)<=16:value='+'+digits[2:]
        elif country=='Lào' and (raw.startswith('+856') or digits.startswith('856')) and 11<=len(digits)<=14:value='+'+digits
        elif country=='Lào' and digits.startswith('020') and 10<=len(digits)<=11:value=digits
        elif len(digits)==10 and re.match(r'^0[35789]',digits):value=digits
        elif len(digits)==11 and digits.startswith('84') and digits[2] in '35789':value='0'+digits[2:]
        elif len(digits)==11 and digits.startswith('02'):value=digits
        if value:
            if value not in valid:valid.append(value)
        else:
            # Two mobile numbers separated only by whitespace must remain two numbers.
            pieces=list(re.finditer(r'(?<!\d)0[ .()]*[35789](?:[ .()]*\d){8}(?!\d)',raw))
            if pieces:
                for piece in pieces:
                    ph=re.sub(r'\D','',piece.group())
                    if ph not in valid:valid.append(ph)
                rest=raw
                for piece in reversed(pieces):rest=rest[:piece.start()]+' '+rest[piece.end():]
                if len(re.sub(r'\D','',rest))>=8:invalid.append(rest.strip())
            else:invalid.append(raw)
    return valid,invalid

def name_without_phone(text):
    s=PHONE_TOKEN.sub(lambda m:'' if len(re.sub(r'\D','',m.group()))>=8 else m.group(),text)
    s=re.sub(r'(?i)\b(?:SĐT|SDT|ĐT|tel|phone)\s*:?','',s)
    s=re.sub(r'\(\s*\)','',s)
    return clean(s).strip(' -:/,') or clean(text)

def run():
    raw=json.loads((HERE/'raw.json').read_text(encoding='utf-8'))
    candidates=[];excluded=[];original=[]
    for f in raw:
        source_region='Miền Bắc' if f['file'].startswith('Data') else 'Miền Trung'
        for sh in f['sheets']:
            section=''
            for r in sh['data']:
                v={c['column']:clean(c['value']) for c in r['cells']}
                if r['row']<=2:continue
                if not v.get(2) and not v.get(3):
                    if v.get(4):section=v[4]
                    continue
                code=v.get(2,'');raw_name=v.get(3,'')
                if norm(code) in ('kl','dl','npp') and norm(raw_name) in ('khach le','dai ly','nha phan phoi') and not v.get(4):
                    excluded.append({'file':f['file'],'sheet':sh['name'],'row':r['row'],'reason':'Dòng danh mục phân loại, không phải đại lý cụ thể'});continue
                if not raw_name:excluded.append({'file':f['file'],'sheet':sh['name'],'row':r['row'],'reason':'Thiếu tên'});continue
                address=v.get(4,'');area=v.get(5,'');notes=v.get(8,'');extra=v.get(9,'')
                region,province,district,issues,evidence=geography(address,area,section,source_region)
                customer_phones,bad=phones(raw_name,province)
                contact_notes=[];transport=[];uncertain=[]
                for line in notes.split('\n'):
                    line=clean(line)
                    if not line:continue
                    if TRANSPORT.search(norm(line)):
                        transport.append(line)
                        # A receiver is kept as an unverified secondary contact, never as the carrier's phone.
                        receiver=re.split(r'(?i)người nhận\s*:',line)
                        if len(receiver)>1:uncertain.append('Người nhận trong ghi chú vận chuyển: '+receiver[-1])
                    else:
                        contact_notes.append(line)
                        if re.search(r'\b(chu|sdt|lien he|dt|phone)\b',norm(line)):
                            good,bad2=phones(line,province)
                            customer_phones.extend(x for x in good if x not in customer_phones)
                            bad.extend(bad2)
                if TRANSPORT.search(norm(area)):
                    transport.insert(0,area);issues.append('Ô khu vực gốc chứa hướng dẫn vận chuyển, không dùng làm địa điểm')
                if extra:uncertain.append('Cột bổ sung không có tiêu đề: '+extra)
                if bad:issues.append('Số điện thoại không đủ/không đúng định dạng: '+' / '.join(dict.fromkeys(bad)))
                if not customer_phones:issues.append('Chưa có số điện thoại khách hợp lệ')
                if not address:issues.append('Thiếu địa chỉ')
                if uncertain:issues.append('Có liên hệ/ghi chú bổ sung chưa rõ vai trò')
                source={'file':f['file'],'sheet':sh['name'],'row':r['row']}
                rec={'code':code,'name':name_without_phone(raw_name),'name_raw':raw_name,'address':address,'region':region,'province':province,'district':district,
                    'phones':customer_phones,'phone_candidates':list(dict.fromkeys(bad)),'kind':v.get(6,''),'sales_rep':v.get(7,''),
                    'customer_notes':'\n'.join(contact_notes),'transport_notes':'\n'.join(transport),'uncertain_notes':'\n'.join(uncertain),
                    'area_raw':area,'source_region':source_region,'geo_evidence':evidence,'issues':issues,'sources':[source]}
                # Merge only matching customer code + matching display name + matching address.
                # A blank code additionally needs the same phone, and remains source-local.
                rec['_key']=norm(code)+'|'+norm(rec['name'])+'|'+norm(address) if code else f["file"]+'|'+norm(rec['name'])+'|'+norm(address)+'|'+','.join(customer_phones)
                candidates.append(rec)
                original.append({'file':f['file'],'sheet':sh['name'],'row':r['row'],'values':[v.get(i,'') for i in range(1,10)]})
    groups=collections.OrderedDict()
    for rec in candidates:groups.setdefault(rec['_key'],[]).append(rec)
    records=[]
    for key,group in groups.items():
        merged=dict(group[0]);merged['id']='DL-'+hashlib.sha256(key.encode()).hexdigest()[:12].upper()
        merged.pop('_key',None)
        merged['sources']=[src for r in group for src in r['sources']]
        merged['source_count']=len(merged['sources'])
        merged['phones']=list(dict.fromkeys(p for r in group for p in r['phones']))
        merged['issues']=list(dict.fromkeys(i for r in group for i in r['issues']))
        for field in ['name_raw','customer_notes','transport_notes','uncertain_notes','area_raw','source_region','kind','sales_rep','phone_candidates']:
            values=[]
            for r in group:
                vs=r[field] if isinstance(r[field],list) else [r[field]]
                values.extend(x for x in vs if x and x not in values)
            merged[field]='\n'.join(values)
        known=[set(r['phones']) for r in group if r['phones']]
        if len(known)>1 and any(x!=known[0] for x in known[1:]):merged['issues'].append('Các dòng trùng tên/địa chỉ có số khách khác nhau; giữ tất cả để xác minh')
        if len(set(norm(r['kind']) for r in group if r['kind']))>1:merged['issues'].append('Phân loại đối tượng không thống nhất giữa các dòng gốc')
        # Missing phone in a duplicate row has been resolved when another matching row supplies it.
        if merged['phones']:merged['issues']=[i for i in merged['issues'] if i!='Chưa có số điện thoại khách hợp lệ']
        records.append(merged)
    by_code=collections.defaultdict(list)
    for rec in records:
        if rec['code']:by_code[norm(rec['code'])].append(rec)
    for code,rs in by_code.items():
        if len(rs)>1:
            for r in rs:r['issues'].append('Cùng mã gốc có nhiều tên/địa chỉ; không tự gộp: '+', '.join(x['id'] for x in rs if x['id']!=r['id']))
    records.sort(key=lambda r:(norm(r['region']),norm(r['province']),norm(r['district']),norm(r['name']),r['id']))
    summary={'source_rows':len(candidates),'unique_records':len(records),'merged_duplicates':len(candidates)-len(records),'excluded_classification_rows':len(excluded),
        'by_region':dict(collections.Counter(r['region'] for r in records)),'with_valid_customer_phone':sum(bool(r['phones']) for r in records),
        'needs_review':sum(bool(r['issues']) for r in records),'with_transport_notes':sum(bool(r['transport_notes']) for r in records),'import_date':'2026-10-24'}
    result={'summary':summary,'records':records,'source_rows':original,'excluded':excluded}
    (HERE/'normalized.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
