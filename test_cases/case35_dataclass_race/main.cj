// case35: 数据类成员竞争测试
// 测试数据类(DataClass)成员的数据竞争

data class DataItem {
    public var id: Int64
    public var name: String
}

main() {
    let item = DataItem(id: 1, name: "test")
    
    spawn {
        item.id = 100  // 写操作
    }
    
    spawn {
        item.id = 200  // 写操作
    }
    
    spawn {
        let currentId = item.id  // 读操作
    }
}