def valida_cif(cif):
    cif=cif.upper()
    nums=[int(x) for x in cif[1:8]]
    s1=sum(divmod(n*2,10)[0]+divmod(n*2,10)[1] for i,n in enumerate(nums) if i%2==0)
    s2=sum(n for i,n in enumerate(nums) if i%2==1)
    c=(10-(s1+s2)%10)%10
    tabla="JABCDEFGHI"
    letra=cif[0]
    ctrl_esp = tabla[c] if letra in "PQRSNW" else str(c) if letra in "ABEH" else (str(c),tabla[c])
    return cif[-1]==ctrl_esp if isinstance(ctrl_esp,str) else cif[-1] in ctrl_esp

# Probar con el CIF problemático
print('Validando CIF R0800391E:', valida_cif('R0800391E'))
