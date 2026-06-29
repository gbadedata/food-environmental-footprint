import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings; warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid"); plt.rcParams["figure.dpi"]=120

# ---------- LOAD & CLEAN ----------
d = pd.read_csv("data/food_production.csv"); d.columns=[c.strip() for c in d.columns]
d = d.rename(columns={"Packging":"Packaging"})
STAGES = ["Land use change","Animal Feed","Farm","Processing","Transport","Packaging","Retail"]

def col(prefix):  # robust lookup to avoid unicode-exact typing
    hits=[c for c in d.columns if c.startswith(prefix)]
    return hits[0]
GHG   = "Total_emissions"
LAND  = col("Land use per kilogram")
WATER = col("Freshwater withdrawals per kilogram")
EUT   = col("Eutrophying emissions per kilogram")
SCW   = col("Scarcity-weighted water use per kilogram")
GHG_P = col("Greenhouse gas emissions per 100g protein")
LAND_P= col("Land use per 100g protein")
IMPACTS = {"GHG (kg CO2e/kg)":GHG, "Land (m2/kg)":LAND, "Water (L/kg)":WATER, "Eutrophication (gPO4e/kg)":EUT}

ANIMAL = {"Beef (beef herd)","Beef (dairy herd)","Lamb & Mutton","Cheese","Milk","Eggs",
          "Pig Meat","Poultry Meat","Fish (farmed)","Shrimps (farmed)"}
d["type"] = np.where(d["Food product"].isin(ANIMAL), "Animal", "Plant")
print("Foods:",len(d),"| animal:",(d.type=="Animal").sum(),"plant:",(d.type=="Plant").sum())

# ---------- FIG 1: GHG ranking, animal vs plant ----------
top = d.nlargest(15, GHG).sort_values(GHG)
plt.figure(figsize=(8,6))
colors = top["type"].map({"Animal":"#c44e52","Plant":"#55a868"})
plt.barh(top["Food product"], top[GHG], color=colors)
plt.xlabel("kg CO2e per kg of product"); plt.title("Greenhouse-gas footprint per kg — top 15 foods")
import matplotlib.patches as mp
plt.legend(handles=[mp.Patch(color="#c44e52",label="Animal"),mp.Patch(color="#55a868",label="Plant")])
plt.tight_layout(); plt.savefig("figures/01_ghg_ranking.png"); plt.close()
print("\nTop GHG foods:"); print(top.nlargest(5,GHG)[["Food product",GHG]].to_string(index=False))

# ---------- FIG 2: stage decomposition + 'food miles' myth ----------
t10 = d.nlargest(10, GHG).set_index("Food product")[STAGES]
plt.figure(figsize=(10,6))
bottom=np.zeros(len(t10)); palette=sns.color_palette("tab10",len(STAGES))
for i,s in enumerate(STAGES):
    plt.bar(t10.index, t10[s], bottom=bottom, label=s, color=palette[i]); bottom+=t10[s].values
plt.xticks(rotation=40, ha="right"); plt.ylabel("kg CO2e per kg"); plt.title("Where do emissions come from? GHG by supply-chain stage")
plt.legend(ncol=2, fontsize=8); plt.tight_layout(); plt.savefig("figures/02_stage_decomposition.png"); plt.close()

an = d[d.type=="Animal"].copy()
for s in STAGES: an[s+"_sh"]=an[s]/an[GHG]
trans_pack = (an["Transport_sh"]+an["Packaging_sh"]).mean()*100
farm_feed_luc = (an["Farm_sh"]+an["Animal Feed_sh"]+an["Land use change_sh"]).mean()*100
print(f"\nAcross animal products (mean share of GHG):")
print(f"  Transport + Packaging = {trans_pack:.1f}%   <-- the 'food miles' the public worries about")
print(f"  Farm + Feed + Land-use change = {farm_feed_luc:.1f}%   <-- where it actually is")
# beef specifically
bf=d[d["Food product"]=="Beef (beef herd)"].iloc[0]
print(f"  Beef: transport is just {bf['Transport']/bf[GHG]*100:.1f}% of its footprint")

# ---------- FIG 3: does the carbon ranking hold across impacts? ----------
fig,(a1,a2)=plt.subplots(1,2,figsize=(13,5))
cor=d[[GHG,LAND,WATER,EUT]].corr(); cor.index=list(IMPACTS.keys()); cor.columns=list(IMPACTS.keys())
sns.heatmap(cor,annot=True,fmt=".2f",cmap="RdYlGn_r",vmin=-1,vmax=1,ax=a1,cbar_kws={"shrink":.8})
a1.set_title("Are the impacts correlated?")
sns.scatterplot(data=d,x=GHG,y=WATER,hue="type",palette={"Animal":"#c44e52","Plant":"#55a868"},s=60,ax=a2)
for _,r in d.iterrows():
    if r[WATER]>d[WATER].quantile(.9) or r[GHG]>d[GHG].quantile(.9):
        a2.annotate(r["Food product"],(r[GHG],r[WATER]),fontsize=7,alpha=.8)
a2.set_xlabel("GHG (kg CO2e/kg)"); a2.set_ylabel("Freshwater (L/kg)"); a2.set_title("Water is the exception: some plants are thirsty")
plt.tight_layout(); plt.savefig("figures/03_multi_impact.png"); plt.close()
print("\nImpact correlations with GHG:")
print(f"  Land r={cor.iloc[0,1]:.2f} | Water r={cor.iloc[0,2]:.2f} | Eutrophication r={cor.iloc[0,3]:.2f}")

# ---------- FIG 4: PCA of impact profiles ----------
feat=[GHG,LAND,WATER,EUT]
dd=d.dropna(subset=feat).reset_index(drop=True).copy()
print(f"\nMultivariate step (PCA/clustering): using {len(dd)} of {len(d)} foods with complete impact data "
      f"({len(d)-len(dd)} dropped for missing values).")
X=StandardScaler().fit_transform(dd[feat])
pca=PCA(n_components=2); pc=pca.fit_transform(X)
dd["PC1"],dd["PC2"]=pc[:,0],pc[:,1]
plt.figure(figsize=(8.5,6.5))
sns.scatterplot(data=dd,x="PC1",y="PC2",hue="type",palette={"Animal":"#c44e52","Plant":"#55a868"},s=70)
for _,r in dd.iterrows():
    if abs(r.PC1)>2 or abs(r.PC2)>2:
        plt.annotate(r["Food product"],(r.PC1,r.PC2),fontsize=7,alpha=.8)
plt.title(f"Foods in impact-space (PCA)\nPC1={pca.explained_variance_ratio_[0]*100:.0f}% (overall impact), PC2={pca.explained_variance_ratio_[1]*100:.0f}% (water axis)")
plt.tight_layout(); plt.savefig("figures/04_pca.png"); plt.close()
print(f"PCA explained variance: PC1={pca.explained_variance_ratio_[0]*100:.0f}%, PC2={pca.explained_variance_ratio_[1]*100:.0f}%")

# ---------- FIG 5: clustering into impact archetypes ----------
k=4; dd["cluster"]=KMeans(n_clusters=k,n_init=10,random_state=42).fit_predict(X)
plt.figure(figsize=(8.5,6.5))
sns.scatterplot(data=dd,x="PC1",y="PC2",hue="cluster",palette="Set2",s=70,style="type")
for _,r in dd.iterrows():
    if abs(r.PC1)>2 or abs(r.PC2)>2:
        plt.annotate(r["Food product"],(r.PC1,r.PC2),fontsize=7,alpha=.75)
plt.title("Four environmental archetypes (k-means on GHG/land/water/eutrophication)")
plt.tight_layout(); plt.savefig("figures/05_clusters.png"); plt.close()
prof=dd.groupby("cluster").agg(n=("Food product","size"),GHG=(GHG,"mean"),Land=(LAND,"mean"),
      Water=(WATER,"mean"),Eutroph=(EUT,"mean"),pct_animal=("type",lambda s:(s=="Animal").mean()*100)).round(1).sort_values("GHG")
print("\nCluster profiles (mean per-kg impacts):"); print(prof.to_string())
for cl in prof.index:
    ex=dd[dd.cluster==cl]["Food product"].head(5).tolist(); print(f"  cluster {cl}: {', '.join(ex)}")

# ---------- FIG 6: fair comparison PER 100g PROTEIN (genuine protein sources only) ----------
# Per-100g-protein is only meaningful for foods eaten as protein sources; for low-protein foods
# (chocolate, coffee, tomatoes...) the figure explodes purely because the denominator is tiny.
PROTEIN_FOODS = {"Beef (beef herd)","Beef (dairy herd)","Lamb & Mutton","Pig Meat","Poultry Meat",
                 "Fish (farmed)","Shrimps (farmed)","Eggs","Cheese","Milk",
                 "Tofu","Soymilk","Peas","Other Pulses","Groundnuts","Nuts"}
prot=d[d["Food product"].isin(PROTEIN_FOODS)].dropna(subset=[GHG_P]).copy()
topp=prot.sort_values(GHG_P)
plt.figure(figsize=(8,6.5))
colors=topp["type"].map({"Animal":"#c44e52","Plant":"#55a868"})
plt.barh(topp["Food product"],topp[GHG_P],color=colors)
plt.xlabel("kg CO2e per 100g of protein"); plt.title("Fair comparison: GHG per 100g of protein (protein sources only)")
plt.legend(handles=[mp.Patch(color="#c44e52",label="Animal"),mp.Patch(color="#55a868",label="Plant")])
plt.tight_layout(); plt.savefig("figures/06_per_protein.png"); plt.close()
print("\nGHG per 100g protein (protein sources only) — worst 5 and best 5:")
print(prot.nlargest(5,GHG_P)[["Food product",GHG_P]].to_string(index=False))
print("...")
print(prot.nsmallest(5,GHG_P)[["Food product",GHG_P]].to_string(index=False))

# ---------- SAVE ARTIFACTS ----------
out=dd[["Food product","type",GHG,LAND,WATER,EUT,"PC1","PC2","cluster"]].copy()
out.columns=["food","type","ghg_kg","land_kg","water_kg","eutroph_kg","PC1","PC2","cluster"]
out.to_csv("data/food_impacts_processed.csv",index=False)
print("\nAll 6 figures + processed data saved. DONE.")
