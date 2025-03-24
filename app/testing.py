st="  double  spaces   "
tmp = st.split()
res=[]
[res.append(word[::-1]) for word in tmp]
final_res = ' '.join(res)
print(final_res)


